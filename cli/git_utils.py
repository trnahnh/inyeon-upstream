import subprocess


class GitError(Exception):
    """Raised when a git command fails."""

    pass


def run_git(args: list[str], check: bool = False) -> tuple[str, str, int]:
    """Run a git command."""
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


def get_repo_id() -> str:
    """Get unique repo identifier from remote URL or directory name."""
    stdout, _, code = run_git(["remote", "get-url", "origin"])
    if code == 0 and stdout.strip():
        url = stdout.strip()
        url = url.replace("git@github.com:", "github.com/")
        url = url.replace("https://", "").replace(".git", "")
        return url

    stdout, _, _ = run_git(["rev-parse", "--show-toplevel"])
    if stdout.strip():
        return stdout.strip().split("/")[-1].split("\\")[-1]

    return "unknown-repo"


def get_staged_diff() -> str:
    """Get diff of staged changes."""
    stdout, _, _ = run_git(["diff", "--cached"])
    return stdout


def get_unstaged_diff() -> str:
    """Get diff of unstaged changes."""
    stdout, _, _ = run_git(["diff"])
    return stdout


def get_all_diff() -> str:
    """Get diff of all uncommitted changes."""
    stdout, _, _ = run_git(["diff", "HEAD"])
    return stdout


def create_commit(message: str) -> bool:
    """Create a commit with the given message."""
    _, _, code = run_git(["commit", "-m", message])
    return code == 0


def get_current_branch() -> str:
    """Get the name of the current branch."""
    stdout, _, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return stdout.strip()


def get_tracked_files() -> list[str]:
    """Get list of all tracked files in the repo."""
    stdout, _, _ = run_git(["ls-files"])
    return [f for f in stdout.strip().split("\n") if f]


def stage_files(files: list[str]) -> bool:
    if not files:
        return True
    result = subprocess.run(
        ["git", "add"] + files,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"Failed to stage files: {result.stderr}")
    return True


def unstage_all() -> bool:
    result = subprocess.run(
        ["git", "reset", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
