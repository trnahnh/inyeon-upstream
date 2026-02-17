import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from cli.api_client import APIClient
from cli.git_utils import (
    is_git_repo,
    get_staged_diff,
    get_all_diff,
    get_current_branch,
    get_branch_commits,
    stage_files,
    unstage_all,
    create_commit,
    GitError,
)
from cli.pipeline import Pipeline, PipelineResult

app = typer.Typer(help="Run full git workflow automation")
console = Console()


@app.callback(invoke_without_command=True)
def auto(
    ctx: typer.Context,
    staged: bool = typer.Option(False, "--staged", "-s", help="Use staged changes"),
    all_changes: bool = typer.Option(False, "--all", "-a", help="Use all uncommitted changes"),
    no_review: bool = typer.Option(False, "--no-review", help="Skip code review"),
    no_pr: bool = typer.Option(False, "--no-pr", help="Skip PR description"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without committing"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
    base_branch: str = typer.Option("main", "--branch", "-b", help="Base branch for PR"),
    api_url: str = typer.Option(None, "--api", envvar="INYEON_API_URL"),
):
    """Run the full workflow: split, commit, review, PR."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    if staged:
        diff = get_staged_diff()
    elif all_changes:
        diff = get_all_diff()
    else:
        console.print("[red]Error:[/red] Specify --staged or --all")
        raise typer.Exit(1)

    if not diff.strip():
        console.print("[yellow]No changes to process[/yellow]")
        raise typer.Exit(0)

    branch_name = get_current_branch()
    commits = get_branch_commits(base_branch)
    client = APIClient(base_url=api_url)
    pipeline = Pipeline(client)

    with console.status("[bold blue]Running pipeline..."):
        result = pipeline.run(
            diff=diff,
            commits=commits,
            branch_name=branch_name,
            base_branch=base_branch,
            skip_review=no_review,
            skip_pr=no_pr,
        )

    if json_output:
        console.print(json.dumps({
            "steps_completed": result.steps_completed,
            "steps_skipped": result.steps_skipped,
            "splits": result.splits,
            "commit_message": result.commit_message,
            "review": result.review,
            "pr_description": result.pr_description,
            "error": result.error,
        }, indent=2))
        raise typer.Exit(0 if not result.error else 1)

    if result.error:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(1)

    _display_result(result)

    if dry_run:
        console.print("\n[dim]--dry-run: No commits created[/dim]")
        raise typer.Exit(0)

    if result.splits:
        if Confirm.ask("\nCreate these commits?"):
            _execute_splits(result.splits)
        else:
            console.print("[dim]Cancelled[/dim]")
    elif result.commit_message:
        if Confirm.ask("\nCreate this commit?"):
            _execute_single(result.commit_message)
        else:
            console.print("[dim]Cancelled[/dim]")


def _display_result(result: PipelineResult) -> None:
    completed = ", ".join(result.steps_completed) or "none"
    skipped = ", ".join(result.steps_skipped) or "none"
    console.print(Panel(
        f"[green]Completed:[/green] {completed}\n[dim]Skipped:[/dim] {skipped}",
        title="Pipeline Result",
        border_style="green",
    ))

    if result.splits:
        console.print(f"\n[bold]Commits ({len(result.splits)}):[/bold]")
        for idx, split in enumerate(result.splits, 1):
            console.print(f"  [{idx}] {split['commit_message']}")
            files = ", ".join(split["files"][:3])
            if len(split["files"]) > 3:
                files += "..."
            console.print(f"      [dim]{files}[/dim]")
    elif result.commit_message:
        console.print(f"\n[bold]Commit:[/bold] {result.commit_message}")

    if result.review:
        score = result.review.get("quality_score", "N/A")
        console.print(f"\n[bold]Review:[/bold] Score {score}/10")
        for issue in result.review.get("issues", [])[:3]:
            console.print(f"  [yellow]![/yellow] {issue.get('description', '')}")

    if result.pr_description:
        console.print(f"\n[bold]PR Title:[/bold] {result.pr_description.get('title', '')}")


def _execute_splits(splits: list) -> None:
    created = 0
    for idx, split in enumerate(splits, 1):
        try:
            unstage_all()
            stage_files(split["files"])
            create_commit(split["commit_message"])
            console.print(f"[green]{chr(10003)}[/green] [{idx}] {split['commit_message'][:60]}")
            created += 1
        except GitError as e:
            console.print(f"[red]x[/red] [{idx}] Failed: {e}")

    console.print(f"\n[bold]Created {created}/{len(splits)} commits.[/bold]")


def _execute_single(message: str) -> None:
    try:
        if create_commit(message):
            console.print("[green]Commit created[/green]")
        else:
            console.print("[red]Failed to create commit[/red]")
    except GitError as e:
        console.print(f"[red]Error:[/red] {e}")
