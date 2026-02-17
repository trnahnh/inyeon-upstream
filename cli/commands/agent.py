import typer
from rich.console import Console
from rich.markup import escape
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


app = typer.Typer(help="Agentic git workflows")
console = Console()


@app.callback(invoke_without_command=True)
def agent(
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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Preview without committing",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show agent reasoning steps",
    ),
    api_url: str = typer.Option(
        None,
        "--api",
        help="Backend API URL",
        envvar="INYEON_API_URL",
    ),
):
    """
    Run the agentic git workflow.

    The agent analyzes changes, gathers context if needed,
    and generates a commit message.

    \b
    Examples:
        inyeon agent --staged
        inyeon agent -s --verbose
        inyeon agent -s --dry-run
    """
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    if staged:
        diff = get_staged_diff()
        if not diff.strip():
            console.print("[yellow]No staged changes[/yellow]")
            raise typer.Exit(0)
    elif all_changes:
        diff = get_all_diff()
        if not diff.strip():
            console.print("[yellow]No uncommitted changes[/yellow]")
            raise typer.Exit(0)
    else:
        console.print("[red]Error:[/red] Specify --staged or --all")
        raise typer.Exit(1)

    client = APIClient(base_url=api_url)

    try:
        with console.status("[bold blue]Agent analyzing changes..."):
            result = client.run_agent(diff, verbose=verbose)
    except APIError as e:
        console.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)

    if verbose and result.get("reasoning"):
        console.print(
            Panel(
                "\n".join(f"• {r}" for r in result["reasoning"]),
                title="Agent Reasoning",
                border_style="dim",
            )
        )

    console.print(
        Panel(
            result["commit_message"],
            title="Generated Commit",
            border_style="green",
        )
    )

    if dry_run:
        console.print("\n[dim]--dry-run: No commit created[/dim]")
        raise typer.Exit(0)

    console.print()
    if Confirm.ask("Create this commit?"):
        try:
            if create_commit(result["commit_message"]):
                console.print("[green]Commit created[/green]")
            else:
                console.print("[red]Failed to create commit[/red]")
                raise typer.Exit(1)
        except GitError as e:
            console.print(f"[red]Error:[/red] {escape(str(e))}")
            raise typer.Exit(1)
    else:
        console.print("[dim]Commit cancelled[/dim]")
