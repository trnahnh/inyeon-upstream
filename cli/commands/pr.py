import json

import typer
from rich.console import Console
from rich.panel import Panel

from cli.api_client import APIClient, APIError
from cli.git_utils import (
    is_git_repo,
    get_staged_diff,
    get_branch_diff,
    get_branch_commits,
    get_current_branch,
)

app = typer.Typer(help="Generate pull request descriptions")
console = Console()


def _display_pr(pr: dict) -> None:
    console.print()
    console.print(Panel(
        pr.get("title", "Untitled"),
        title="PR Title",
        border_style="green",
    ))

    summary = pr.get("summary", "")
    if summary:
        console.print(f"\n[bold]Summary:[/bold]\n  {summary}")

    changes = pr.get("changes", [])
    if changes:
        console.print(f"\n[bold]Changes:[/bold]")
        for change in changes:
            console.print(f"  {change}")

    testing = pr.get("testing", "")
    if testing:
        console.print(f"\n[bold]Testing:[/bold]\n  {testing}")

    breaking = pr.get("breaking_changes", [])
    if breaking:
        console.print(f"\n[bold red]Breaking Changes:[/bold red]")
        for b in breaking:
            console.print(f"  [red]![/red] {b}")


@app.callback(invoke_without_command=True)
def pr(
    ctx: typer.Context,
    staged: bool = typer.Option(False, "--staged", "-s", help="Use staged changes only"),
    branch: str = typer.Option(None, "--branch", "-b", help="Base branch to compare against"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
    api_url: str = typer.Option(None, "--api", envvar="INYEON_API_URL"),
):
    """Generate a pull request description from branch changes."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    base_branch = branch or "main"
    current = get_current_branch()

    if staged:
        diff = get_staged_diff()
        commits = []
    else:
        diff = get_branch_diff(base_branch)
        commits = get_branch_commits(base_branch)

    if not diff.strip():
        console.print(f"[yellow]No changes between {current} and {base_branch}[/yellow]")
        raise typer.Exit(0)

    client = APIClient(base_url=api_url)

    with console.status("[bold blue]Generating PR description..."):
        try:
            result = client.generate_pr(
                diff=diff,
                commits=commits,
                branch_name=current,
                base_branch=base_branch,
            )
        except APIError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if result.get("error"):
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result, indent=2))
        raise typer.Exit(0)

    pr_desc = result.get("pr_description")
    if pr_desc:
        _display_pr(pr_desc)
    else:
        console.print("[yellow]No PR description generated[/yellow]")
