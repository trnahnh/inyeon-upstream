import json

import typer
from rich.console import Console
from rich.panel import Panel

from cli.api_client import APIClient, APIError
from cli.git_utils import is_git_repo, get_staged_diff, get_all_diff


app = typer.Typer(help="Review code changes")
console = Console()


def _display_review(result: dict) -> None:
    """Display review with rich formatting."""
    review = result.get("review", {})

    # Summary
    console.print()
    score = review.get("quality_score", "N/A")
    score_color = "green" if score >= 7 else "yellow" if score >= 5 else "red"
    console.print(
        Panel(
            review.get("summary", "No summary"),
            title=f"Review [bold {score_color}]Score: {score}/10[/bold {score_color}]",
            border_style=score_color,
        )
    )

    # Issues
    issues = review.get("issues", [])
    if issues:
        console.print("\n[bold red]Issues:[/bold red]")
        for issue in issues:
            severity = issue.get("severity", "medium")
            color = {"high": "red", "medium": "yellow", "low": "dim"}.get(
                severity, "white"
            )
            console.print(
                f"  [{color}][{severity.upper()}][/{color}] {issue.get('description', '')}"
            )
            if issue.get("suggestion"):
                console.print(f"    [dim]→ {issue['suggestion']}[/dim]")

    # Positives
    positives = review.get("positives", [])
    if positives:
        console.print("\n[bold green]Positives:[/bold green]")
        for pos in positives:
            console.print(f"  [green]✓[/green] {pos}")

    # Suggestions
    suggestions = review.get("suggestions", [])
    if suggestions:
        console.print("\n[bold blue]Suggestions:[/bold blue]")
        for sug in suggestions:
            console.print(f"  [blue]•[/blue] {sug}")


@app.callback(invoke_without_command=True)
def review(
    ctx: typer.Context,
    staged: bool = typer.Option(False, "--staged", "-s", help="Review staged changes"),
    all_changes: bool = typer.Option(
        False, "--all", "-a", help="Review all uncommitted changes"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
    api_url: str = typer.Option(
        None, "--api", help="Backend API URL", envvar="INYEON_API_URL"
    ),
):
    """Review code changes and get feedback."""
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

    console.print("[dim]Reviewing code...[/dim]")
    client = APIClient(base_url=api_url)

    try:
        result = client.review(diff)
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result, indent=2))
    else:
        _display_review(result)
