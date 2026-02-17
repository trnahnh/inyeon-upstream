import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from cli.api_client import APIClient, APIError
from cli.git_utils import (
    is_git_repo,
    get_merge_conflicts,
    get_conflict_content,
    get_ours_version,
    get_theirs_version,
    write_resolved_file,
    stage_files,
)

app = typer.Typer(help="Resolve merge conflicts with AI")
console = Console()

STRATEGY_COLORS = {
    "ours": "blue",
    "theirs": "yellow",
    "merge": "green",
    "rewrite": "magenta",
}


@app.callback(invoke_without_command=True)
def resolve(
    ctx: typer.Context,
    file: str = typer.Option(None, "--file", "-f", help="Resolve a single file"),
    all_conflicts: bool = typer.Option(False, "--all", "-a", help="Resolve all conflicts"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
    api_url: str = typer.Option(None, "--api", envvar="INYEON_API_URL"),
):
    """Resolve merge conflicts using AI analysis."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    if file:
        paths = [file]
    elif all_conflicts:
        paths = get_merge_conflicts()
    else:
        console.print("[red]Error:[/red] Specify --file or --all")
        raise typer.Exit(1)

    if not paths:
        console.print("[yellow]No merge conflicts found[/yellow]")
        raise typer.Exit(0)

    conflicts = []
    for path in paths:
        conflicts.append({
            "path": path,
            "content": get_conflict_content(path),
            "ours": get_ours_version(path),
            "theirs": get_theirs_version(path),
        })

    client = APIClient(base_url=api_url)

    with console.status("[bold blue]Resolving conflicts..."):
        try:
            result = client.resolve_conflicts(conflicts)
        except APIError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if result.get("error"):
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result, indent=2))
        raise typer.Exit(0)

    resolutions = result.get("resolutions", [])
    if not resolutions:
        console.print("[yellow]No resolutions generated[/yellow]")
        raise typer.Exit(0)

    _apply_resolutions(resolutions)


def _apply_resolutions(resolutions: list[dict]) -> None:
    applied = 0
    for res in resolutions:
        path = res["path"]
        strategy = res.get("strategy", "unknown")
        explanation = res.get("explanation", "")
        color = STRATEGY_COLORS.get(strategy, "white")

        console.print(Panel(
            f"[{color}]{strategy}[/{color}]: {explanation}",
            title=path,
            border_style=color,
        ))

        if strategy == "error":
            console.print(f"  [red]Skipped (resolution failed)[/red]")
            continue

        if Confirm.ask(f"  Apply resolution to {path}?"):
            write_resolved_file(path, res["resolved_content"])
            stage_files([path])
            console.print(f"  [green]Applied and staged[/green]")
            applied += 1
        else:
            console.print(f"  [dim]Skipped[/dim]")

    console.print(f"\n[bold]Resolved {applied}/{len(resolutions)} conflict(s).[/bold]")
