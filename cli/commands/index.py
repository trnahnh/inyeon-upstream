from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from cli.api_client import APIClient, APIError
from cli.git_utils import is_git_repo, get_repo_id, get_tracked_files

app = typer.Typer(help="Index codebase for RAG search")
console = Console()

INDEXABLE_EXTENSIONS = {
    # Python
    ".py",
    ".pyi",
    # JavaScript/TypeScript
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".mjs",
    ".cjs",
    # Web
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
    # Systems
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".rs",
    ".go",
    # JVM
    ".java",
    ".kt",
    ".scala",
    ".groovy",
    # .NET
    ".cs",
    ".fs",
    ".vb",
    # Scripting
    ".rb",
    ".php",
    ".pl",
    ".lua",
    ".sh",
    ".bash",
    ".zsh",
    # Data/Config
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    # Mobile
    ".swift",
    ".m",
    ".dart",
    # Other
    ".sql",
    ".graphql",
    ".proto",
    ".r",
    ".jl",
}
MAX_FILE_SIZE = 50_000


def _should_index(path: str) -> bool:
    """Check if file should be indexed."""
    p = Path(path)
    if p.suffix not in INDEXABLE_EXTENSIONS:
        return False
    if any(part.startswith(".") for part in p.parts):
        return False
    if "test" in path.lower() or "spec" in path.lower():
        return False
    if "node_modules" in path or "venv" in path or ".venv" in path:
        return False
    return True


def _read_file(path: str) -> str | None:
    """Read file content if within size limit."""
    try:
        p = Path(path)
        if p.stat().st_size > MAX_FILE_SIZE:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


@app.callback(invoke_without_command=True)
def index(
    ctx: typer.Context,
    clear: bool = typer.Option(
        False, "--clear", "-c", help="Clear index before indexing"
    ),
    stats_only: bool = typer.Option(
        False, "--stats", "-s", help="Show index stats only"
    ),
    api_url: str = typer.Option(
        None, "--api", help="Backend API URL", envvar="INYEON_API_URL"
    ),
):
    """Index current repository for RAG-enhanced commits."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    repo_id = get_repo_id()
    client = APIClient(base_url=api_url)

    if stats_only:
        try:
            result = client.rag_stats(repo_id)
            console.print(f"[bold]Repo:[/bold] {repo_id}")
            console.print(f"[bold]Indexed files:[/bold] {result['indexed_files']}")
        except APIError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        return

    if clear:
        try:
            client.rag_clear(repo_id)
            console.print(f"[green]Cleared index for {repo_id}[/green]")
        except APIError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        return

    tracked_files = get_tracked_files()
    files_to_index = [f for f in tracked_files if _should_index(f)]

    if not files_to_index:
        console.print("[yellow]No indexable files found[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]Repo:[/bold] {repo_id}")
    console.print(f"[bold]Files to index:[/bold] {len(files_to_index)}")

    files_content = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Reading files...", total=None)

        for path in files_to_index:
            content = _read_file(path)
            if content:
                files_content[path] = content

        progress.update(task, description=f"Read {len(files_content)} files")

        if not files_content:
            console.print("[yellow]No readable files found[/yellow]")
            raise typer.Exit(0)

        progress.update(task, description="Uploading to index...")

        try:
            result = client.rag_index(repo_id, files_content)
            progress.update(task, description="Done!")
        except APIError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(1)

    console.print(
        f"[green]Indexed {result['indexed']} files (total: {result['total']})[/green]"
    )
