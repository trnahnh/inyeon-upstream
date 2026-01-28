import subprocess


class GitError(Exception):
    """Raised when a git command fails."""

    pass


def run_git(args: list[str], check: bool = False) -> tuple[str, str, int]:
    """
    Run a git command.

    Args:
                    args: Git command arguments (e.g., ["diff", "--cached"]).
                    check: If True, raise GitError on non-zero exit.

    Returns:
                    Tuple of (stdout, stderr, return_code).

    Raises:
                    GitError: If check=True and command fails.
    """
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if check and result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")

    return result.stdout, result.stderr, result.returncode


def is_git_repo() -> bool:
    """Check if current directory is inside a git repository."""
    _, _, code = run_git(["rev-parse", "--git-dir"])
    return code == 0


def get_staged_diff() -> str:
    """Get diff of staged changes."""
    stdout, _, _ = run_git(["diff", "--cached"])
    return stdout


def get_unstaged_diff() -> str:
    """Get diff of unstaged changes (working tree vs index)."""
    stdout, _, _ = run_git(["diff"])
    return stdout


def get_all_diff() -> str:
    """Get diff of all uncommitted changes (staged + unstaged)."""
    stdout, _, _ = run_git(["diff", "HEAD"])
    return stdout


def create_commit(message: str) -> bool:
    """
    Create a commit with the given message.

    Returns:
        True if commit succeeded, False otherwise.
    """
    _, _, code = run_git(["commit", "-m", message])
    return code == 0


def get_current_branch() -> str:
    """Get the name of the current branch."""
    stdout, _, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return stdout.strip()
