import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from cli.api_client import APIClient, APIError
from cli.git_utils import (
    is_git_repo,
    get_staged_diff,
    get_all_diff,
    create_commit,
    GitError,
)


app = typer.Typer(help="Generate commit messages")
console = Console()


def _display_commit(result: dict) -> None:
    """Display generated commit message with rich formatting."""
    # Commit type badge
    type_colors = {
        "feat": "green",
        "fix": "red",
        "docs": "blue",
        "style": "magenta",
        "refactor": "yellow",
        "perf": "cyan",
        "test": "white",
        "build": "white",
        "ci": "white",
        "chore": "dim",
    }
    color = type_colors.get(result["type"], "white")

    scope = f"({result['scope']})" if result.get("scope") else ""
    title = f"[{color}]{result['type']}[/{color}]{scope}"

    console.print()
    console.print(Panel(result["message"], title=title, border_style=color))

    # Show breaking change warning
    if result.get("breaking_change"):
        console.print(
            f"\n[bold red] BREAKING CHANGE:[/bold red] {result['breaking_change']}"
        )


@app.callback(invoke_without_command=True)
def commit(
    ctx: typer.Context,
    staged: bool = typer.Option(
        False,
        "--staged",
        "-s",
        help="Use staged changes only",
    ),
    all_changes: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Use all uncommitted changes",
    ),
    issue: str = typer.Option(
        None,
        "--issue",
        "-i",
        help="Issue reference (e.g., #234)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show message without committing",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output raw JSON response",
    ),
    api_url: str = typer.Option(
        None,
        "--api",
        help="Backend API URL (overrides config)",
        envvar="INYEON_API_URL",
    ),
    hook_mode: bool = typer.Option(
        False,
        "--hook-mode",
        hidden=True,
    ),
):
    """
    Generate a conventional commit message from changes.

    \b
    Examples:
        inyeon commit --staged
        inyeon commit -s --issue "#123"
        inyeon commit -s --dry-run
    """
    # Verify git repo
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    # Get diff
    if staged:
        diff = get_staged_diff()
        if not diff.strip():
            console.print("[yellow]No staged changes[/yellow]")
            console.print("Stage changes with: git add <files>")
            raise typer.Exit(0)
    elif all_changes:
        diff = get_all_diff()
        if not diff.strip():
            console.print("[yellow]No uncommitted changes[/yellow]")
            raise typer.Exit(0)
    else:
        console.print("[red]Error:[/red] Specify --staged or --all")
        console.print("Usage: inyeon commit --staged")
        raise typer.Exit(1)

    # Call backend
    if not hook_mode:
        console.print("[dim]Generating commit message...[/dim]", end="\r")
    client = APIClient(base_url=api_url)

    try:
        result = client.generate_commit(diff, issue)
    except APIError as e:
        if not hook_mode:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if hook_mode:
        print(result.get("message", ""))
        raise typer.Exit(0)

    # Output
    if json_output:
        console.print(json.dumps(result, indent=2))
        raise typer.Exit(0)

    _display_commit(result)

    # Dry run stops here
    if dry_run:
        console.print("\n[dim]--dry-run: No commit created[/dim]")
        raise typer.Exit(0)

    # Confirm and commit
    console.print()
    if not staged:
        console.print("[yellow]Warning:[/yellow] Using --all will commit all changes")

    if Confirm.ask("Create this commit?"):
        try:
            if create_commit(result["message"]):
                console.print("[green] Commit created[/green]")
            else:
                console.print("[red]Failed to create commit[/red]")
                raise typer.Exit(1)
        except GitError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    else:
        console.print("[dim]Commit cancelled[/dim]")
