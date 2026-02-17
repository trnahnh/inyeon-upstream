import json
import sys

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from cli.api_client import APIClient, APIError


app = typer.Typer(help="Analyze git diffs")
console = Console()


def _format_impact(impact: str) -> str:
    """Color-code impact level."""
    colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
    }
    color = colors.get(impact, "white")
    return f"[{color}]{impact.upper()}[/{color}]"


def _display_result(result: dict) -> None:
    """Display analysis result with rich formatting."""
    # Summary panel
    console.print()
    console.print(Panel(result["summary"], title="Summary", border_style="blue"))

    # Impact and categories
    console.print(f"\n[bold]Impact:[/bold] {_format_impact(result['impact'])}")
    if result.get("categories"):
        console.print(f"[bold]Categories:[/bold] {', '.join(result['categories'])}")

    # Breaking changes
    if result.get("breaking_changes"):
        console.print("\n[bold red]Breaking Changes:[/bold red]")
        for change in result["breaking_changes"]:
            console.print(f"  • {change}")

    # Security concerns
    if result.get("security_concerns"):
        console.print("\n[bold yellow]Security Concerns:[/bold yellow]")
        for concern in result["security_concerns"]:
            console.print(f"  • {concern}")

    # Files changed
    if result.get("files_changed"):
        console.print()
        table = Table(title="Files Changed", show_header=True, header_style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Type")
        table.add_column("Summary")

        for file in result["files_changed"]:
            table.add_row(
                file["path"],
                file["change_type"],
                file["summary"],
            )

        console.print(table)


@app.callback(invoke_without_command=True)
def analyze(
    ctx: typer.Context,
    file: str = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to diff file (instead of stdin)",
    ),
    context: str = typer.Option(
        None,
        "--context",
        "-c",
        help="Additional context about the changes",
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
):
    """
    Analyze a git diff and explain the changes.

    \b
    Examples:
        git diff | inyeon analyze
        git diff HEAD~3 | inyeon analyze
        inyeon analyze -f changes.diff
        inyeon analyze -c "Refactoring auth module"
    """
    # Read diff from stdin or file
    if file:
        try:
            with open(file) as f:
                diff_content = f.read()
        except FileNotFoundError:
            console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)
    elif not sys.stdin.isatty():
        diff_content = sys.stdin.read()
    else:
        console.print("[red]Error:[/red] No diff provided")
        console.print("Usage: git diff | inyeon analyze")
        console.print("   or: inyeon analyze -f <file>")
        raise typer.Exit(1)

    if not diff_content.strip():
        console.print("[yellow]No changes to analyze[/yellow]")
        raise typer.Exit(0)

    # Call backend
    console.print("[dim]Analyzing diff...[/dim]", end="\r")
    client = APIClient(base_url=api_url)

    try:
        result = client.analyze(diff_content, context)
    except APIError as e:
        console.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)

    # Output
    if json_output:
        console.print(json.dumps(result, indent=2))
    else:
        _display_result(result)
