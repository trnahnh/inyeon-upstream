import os
import stat

import typer
from rich.console import Console

from cli.git_utils import is_git_repo, run_git

app = typer.Typer(help="Manage git hooks for Inyeon")
console = Console()

HOOK_MARKER = "# inyeon-managed-hook"

HOOK_SCRIPT = f"""#!/bin/sh
{HOOK_MARKER}

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only run for regular commits (not merge, squash, amend)
if [ -z "$COMMIT_SOURCE" ]; then
    MSG=$(inyeon commit --staged --hook-mode 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$MSG" ]; then
        echo "$MSG" > "$COMMIT_MSG_FILE"
    fi
fi
"""


def _hooks_dir() -> str:
    stdout, _, _ = run_git(["rev-parse", "--git-dir"])
    return os.path.join(stdout.strip(), "hooks")


def _hook_path() -> str:
    return os.path.join(_hooks_dir(), "prepare-commit-msg")


def _is_inyeon_hook(path: str) -> bool:
    with open(path, "r") as f:
        return HOOK_MARKER in f.read()


@app.command()
def install():
    """Install Inyeon prepare-commit-msg hook."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    path = _hook_path()

    if os.path.exists(path) and not _is_inyeon_hook(path):
        console.print("[red]Error:[/red] Existing hook is not from Inyeon. Remove it manually first.")
        raise typer.Exit(1)

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="\n") as f:
        f.write(HOOK_SCRIPT)

    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    console.print("[green]Installed prepare-commit-msg hook[/green]")


@app.command()
def remove():
    """Remove Inyeon git hooks."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    path = _hook_path()

    if not os.path.exists(path):
        console.print("[yellow]No hook installed[/yellow]")
        raise typer.Exit(0)

    if not _is_inyeon_hook(path):
        console.print("[red]Error:[/red] Hook is not from Inyeon")
        raise typer.Exit(1)

    os.remove(path)
    console.print("[green]Removed prepare-commit-msg hook[/green]")


@app.command()
def status():
    """Check if Inyeon hooks are installed."""
    if not is_git_repo():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    path = _hook_path()

    if not os.path.exists(path):
        console.print("[dim]No hook installed[/dim]")
        return

    if _is_inyeon_hook(path):
        console.print("[green]Inyeon hook is installed[/green]")
    else:
        console.print("[yellow]prepare-commit-msg hook exists but is not from Inyeon[/yellow]")
