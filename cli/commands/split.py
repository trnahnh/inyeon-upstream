import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from cli.api_client import APIClient, APIError
from cli.git_utils import (
    is_git_repo,
    get_staged_diff,
    get_all_diff,
    GitError,
)

app = typer.Typer(help="Split changes into atomic commits")
console = Console()


@app.callback(invoke_without_command=True)
def split(
    ctx: typer.Context,
    staged: bool = typer.Option(False, "--staged", "-s", help="Use staged changes"),
    all_changes: bool = typer.Option(
        False, "--all", "-a", help="Use all uncommitted changes"
    ),
    strategy: str = typer.Option(
        "hybrid", "--strategy", "-S", help="Clustering strategy"
    ),
    preview: bool = typer.Option(
        False, "--preview", "-p", help="Preview without committing"
    ),
    execute: bool = typer.Option(
        False, "--execute", "-e", help="Auto-commit all groups"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Approve each commit"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
    api_url: str = typer.Option(None, "--api", envvar="INYEON_API_URL"),
):
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
        console.print("[yellow]No changes to split[/yellow]")
        raise typer.Exit(0)

    client = APIClient(base_url=api_url)

    with console.status("[bold blue]Analyzing and splitting changes..."):
        try:
            result = client.split_diff(diff, strategy=strategy)
        except APIError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result, indent=2))
        raise typer.Exit(0)

    if result.get("error"):
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    splits = result.get("splits", [])
    if not splits:
        console.print("[yellow]No split groups created[/yellow]")
        raise typer.Exit(0)

    _display_splits(splits, result.get("total_groups", 0))

    if preview:
        console.print("\n[dim]--preview: No commits created[/dim]")
        raise typer.Exit(0)

    if execute:
        _execute_all(splits)
    elif interactive:
        _interactive_mode(splits)
    else:
        choice = Prompt.ask(
            "\nWhat would you like to do?", choices=["e", "i", "p", "c"], default="i"
        )
        if choice == "e":
            _execute_all(splits)
        elif choice == "i":
            _interactive_mode(splits)
        elif choice == "p":
            console.print("[dim]Preview only - no commits created[/dim]")
        else:
            console.print("[dim]Cancelled[/dim]")


def _display_splits(splits: list, total: int) -> None:
    console.print()
    console.print(
        Panel(f"[bold]Split Result: {total} commit groups[/bold]", border_style="green")
    )

    for idx, split in enumerate(splits, 1):
        color = _get_type_color(split.get("commit_type"))
        console.print(
            f"\n[bold {color}][{idx}/{total}][/bold {color}] {split['commit_message']}"
        )
        console.print(f"  [dim]Files: {len(split['files'])}[/dim]")
        for f in split["files"][:5]:
            console.print(f"    [dim]-[/dim] {f}")
        if len(split["files"]) > 5:
            console.print(f"    [dim]... and {len(split['files']) - 5} more[/dim]")


def _get_type_color(commit_type: str | None) -> str:
    colors = {
        "feat": "green",
        "fix": "red",
        "docs": "blue",
        "refactor": "yellow",
        "test": "cyan",
        "style": "magenta",
        "perf": "cyan",
        "chore": "white",
    }
    return colors.get(commit_type or "", "white")


def _execute_all(splits: list) -> None:
    from cli.git_utils import stage_files, unstage_all, create_commit

    created = 0
    for idx, split in enumerate(splits, 1):
        try:
            unstage_all()
            stage_files(split["files"])
            create_commit(split["commit_message"])
            console.print(f"[green]✓[/green] [{idx}] {split['commit_message'][:50]}")
            created += 1
        except GitError as e:
            console.print(f"[red]✗[/red] [{idx}] Failed: {e}")

    console.print(f"\n[bold]Done! Created {created}/{len(splits)} commits.[/bold]")


def _interactive_mode(splits: list) -> None:
    from cli.git_utils import stage_files, unstage_all, create_commit

    created = 0
    for idx, split in enumerate(splits, 1):
        console.print(f"\n[bold][{idx}/{len(splits)}][/bold] {split['commit_message']}")
        files_preview = ", ".join(split["files"][:3])
        if len(split["files"]) > 3:
            files_preview += "..."
        console.print(f"[dim]Files: {files_preview}[/dim]")

        choice = Prompt.ask("Create this commit?", choices=["y", "n", "e"], default="y")

        if choice == "n":
            console.print("[dim]Skipped[/dim]")
            continue

        message = split["commit_message"]
        if choice == "e":
            message = Prompt.ask("Enter new message", default=message)

        try:
            unstage_all()
            stage_files(split["files"])
            create_commit(message)
            console.print("[green]✓ Commit created[/green]")
            created += 1
        except GitError as e:
            console.print(f"[red]✗ Failed: {e}[/red]")

    console.print(f"\n[bold]Done! Created {created}/{len(splits)} commits.[/bold]")
