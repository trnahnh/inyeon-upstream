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

    try:
        if local:
            import asyncio
            from cli.engine import create_engine
            from cli.display import render_local_stream

            engine = create_engine(local=True, provider=provider)
            if stream:
                result = render_local_stream(
                    engine.generate_commit_stream(diff), console
                )
                if result is None:
                    raise typer.Exit(1)
            else:
                engine_result = asyncio.run(engine.generate_commit(diff))
                if engine_result.error:
                    console.print(f"[red]Error:[/red] {engine_result.error}")
                    raise typer.Exit(1)
                result = engine_result.data
        elif stream:
            client = APIClient(base_url=api_url, provider=provider)
            events = client.generate_commit_stream(diff)
            result = render_stream(events, console)
            if result is None:
                raise typer.Exit(1)
        else:
            client = APIClient(base_url=api_url, provider=provider)
            with console.status("[bold blue]Agent analyzing changes..."):
                result = client.run_agent(diff, verbose=verbose)
    except typer.Exit:
        raise
    except APIError as e:
        console.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)

    if not stream and verbose and result.get("reasoning"):
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
