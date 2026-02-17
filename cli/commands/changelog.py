import json

import typer
from rich.console import Console
from rich.panel import Panel

from cli.api_client import APIClient, APIError
from cli.git_utils import (
    is_git_repo,
    get_commits_between,
    get_commits_since,
    get_tags,
)

app = typer.Typer(help="Generate changelogs from commit history")
console = Console()


@app.callback(invoke_without_command=True)
def changelog(
    ctx: typer.Context,
    from_ref: str = typer.Option(None, "--from", help="Start ref (tag or commit)"),
    to_ref: str = typer.Option("HEAD", "--to", help="End ref"),
    last_days: int = typer.Option(None, "--last", help="Commits from last N days"),
    output: str = typer.Option(None, "--output", "-o", help="Write to file"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
    api_url: str = typer.Option(None, "--api", envvar="INYEON_API_URL"),
):
    """Generate a changelog from commit history."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    if last_days:
        commits = get_commits_since(last_days)
        ref_label = f"last {last_days} days"
    elif from_ref:
        commits = get_commits_between(from_ref, to_ref)
        ref_label = f"{from_ref}..{to_ref}"
    else:
        tags = get_tags()
        if tags:
            from_ref = tags[0]
            commits = get_commits_between(from_ref, to_ref)
            ref_label = f"{from_ref}..{to_ref}"
        else:
            console.print("[red]Error:[/red] Specify --from, --last, or have tags in repo")
            raise typer.Exit(1)

    if not commits:
        console.print(f"[yellow]No commits found for {ref_label}[/yellow]")
        raise typer.Exit(0)

    client = APIClient(base_url=api_url)

    with console.status("[bold blue]Generating changelog..."):
        try:
            result = client.generate_changelog(
                commits=commits,
                from_ref=from_ref or "",
                to_ref=to_ref,
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

    cl = result.get("changelog")
    if not cl:
        console.print("[yellow]No changelog generated[/yellow]")
        raise typer.Exit(0)

    text = _format_changelog(cl)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(text)
        console.print(f"[green]Changelog written to {output}[/green]")
    else:
        _display_changelog(cl)


def _format_changelog(cl: dict) -> str:
    """Format changelog as markdown text."""
    lines: list[str] = []
    version = cl.get("version", "Unreleased")
    date = cl.get("date", "")
    lines.append(f"## {version} ({date})" if date else f"## {version}")
    lines.append("")

    summary = cl.get("summary", "")
    if summary:
        lines.append(summary)
        lines.append("")

    section_titles = {
        "feat": "Features",
        "fix": "Bug Fixes",
        "docs": "Documentation",
        "refactor": "Refactoring",
        "perf": "Performance",
        "test": "Tests",
        "chore": "Chores",
    }

    for key, title in section_titles.items():
        items = cl.get("sections", {}).get(key, [])
        if items:
            lines.append(f"### {title}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)


def _display_changelog(cl: dict) -> None:
    """Display changelog with Rich formatting."""
    version = cl.get("version", "Unreleased")
    date = cl.get("date", "")
    header = f"{version} ({date})" if date else version

    console.print(Panel(header, title="Changelog", border_style="green"))

    summary = cl.get("summary", "")
    if summary:
        console.print(f"\n{summary}")

    section_titles = {
        "feat": ("Features", "green"),
        "fix": ("Bug Fixes", "red"),
        "docs": ("Documentation", "blue"),
        "refactor": ("Refactoring", "yellow"),
        "perf": ("Performance", "cyan"),
        "test": ("Tests", "white"),
        "chore": ("Chores", "dim"),
    }

    for key, (title, color) in section_titles.items():
        items = cl.get("sections", {}).get(key, [])
        if items:
            console.print(f"\n[bold {color}]{title}:[/bold {color}]")
            for item in items:
                console.print(f"  - {item}")
