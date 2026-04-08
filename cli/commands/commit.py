import json
import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm

from cli.api_client import APIClient, APIError
from cli.display import render_stream
from cli.git_utils import (
    is_git_repo,
    get_staged_diff,
    get_all_diff,
    create_commit,
    stage_tracked_changes,
    GitError,
)


app = typer.Typer(help="Generate commit messages")
console = Console()


def _display_commit(result: dict) -> None:
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
    provider: str = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider (openai, gemini, ollama)",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        "-L",
        help="Run locally without backend server",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream agent progress in real-time",
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
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

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

    try:
        if local:
            import asyncio
            from cli.engine import create_engine
            from cli.display import render_local_stream

            engine = create_engine(local=True, provider=provider)
            if stream and not hook_mode:
                result = render_local_stream(
                    engine.generate_commit_stream(diff, issue_ref=issue), console
                )
                if result is None:
                    raise typer.Exit(1)
            else:
                engine_result = asyncio.run(engine.generate_commit(diff, issue_ref=issue))
                if engine_result.error:
                    console.print(f"[red]Error:[/red] {engine_result.error}")
                    raise typer.Exit(1)
                result = engine_result.data
        elif stream and not hook_mode:
            client = APIClient(base_url=api_url, provider=provider)
            events = client.generate_commit_stream(diff, issue_ref=issue)
            result = render_stream(events, console)
            if result is None:
                raise typer.Exit(1)
        else:
            client = APIClient(base_url=api_url, provider=provider)
            if not hook_mode:
                console.print("[dim]Generating commit message...[/dim]", end="\r")
            result = client.generate_commit(diff, issue)
    except typer.Exit:
        raise
    except APIError as e:
        if not hook_mode:
            console.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)

    if hook_mode:
        print(result.get("message", ""))
        raise typer.Exit(0)

    if json_output:
        console.print(json.dumps(result, indent=2))
        raise typer.Exit(0)

    _display_commit(result)

    if dry_run:
        console.print("\n[dim]--dry-run: No commit created[/dim]")
        raise typer.Exit(0)

    console.print()
    if not staged:
        console.print("[yellow]Warning:[/yellow] Using --all will commit all changes")

    if Confirm.ask("Create this commit?"):
        try:
            if not staged:
                stage_tracked_changes()
            if create_commit(result["message"]):
                console.print("[green] Commit created[/green]")
            else:
                console.print("[red]Failed to create commit[/red]")
                raise typer.Exit(1)
        except GitError as e:
            console.print(f"[red]Error:[/red] {escape(str(e))}")
            raise typer.Exit(1)
    else:
        console.print("[dim]Commit cancelled[/dim]")
