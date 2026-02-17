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


def get_branch_diff(base_branch: str = "main") -> str:
    """Get combined diff of current branch against base branch."""
    stdout, _, code = run_git(["diff", f"{base_branch}...HEAD"])
    if code != 0:
        stdout, _, _ = run_git(["diff", f"origin/{base_branch}...HEAD"])
    return stdout


def get_branch_commits(base_branch: str = "main") -> list[dict[str, str]]:
    """Get commit messages from current branch since diverging from base."""
    fmt = "%H|||%s|||%b|||%an"
    stdout, _, code = run_git([
        "log", f"{base_branch}..HEAD",
        f"--pretty=format:{fmt}",
        "--reverse",
    ])
    if code != 0 or not stdout.strip():
        return []

    commits = []
    for line in stdout.strip().split("\n"):
        parts = line.split("|||")
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0][:8],
                "subject": parts[1],
                "body": parts[2],
                "author": parts[3],
            })
    return commits


def unstage_all() -> bool:
    result = subprocess.run(
        ["git", "reset", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_merge_conflicts() -> list[str]:
    """Get list of files with merge conflicts."""
    stdout, _, code = run_git(["diff", "--name-only", "--diff-filter=U"])
    if code != 0 or not stdout.strip():
        return []
    return [f for f in stdout.strip().split("\n") if f]


def get_conflict_content(path: str) -> str:
    """Read file content including conflict markers."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def get_ours_version(path: str) -> str:
    """Get our side of a conflicted file."""
    stdout, _, code = run_git(["show", f":2:{path}"])
    if code != 0:
        return ""
    return stdout


def get_theirs_version(path: str) -> str:
    """Get their side of a conflicted file."""
    stdout, _, code = run_git(["show", f":3:{path}"])
    if code != 0:
        return ""
    return stdout


def write_resolved_file(path: str, content: str) -> None:
    """Write resolved content to a conflicted file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_commits_between(from_ref: str, to_ref: str = "HEAD") -> list[dict[str, str]]:
    """Get commits between two refs."""
    fmt = "%H|||%s|||%b|||%an|||%ai"
    stdout, _, code = run_git([
        "log", f"{from_ref}..{to_ref}",
        f"--pretty=format:{fmt}",
        "--reverse",
    ])
    if code != 0 or not stdout.strip():
        return []
    return _parse_log_output(stdout)


def get_commits_since(days: int) -> list[dict[str, str]]:
    """Get commits from the last N days."""
    fmt = "%H|||%s|||%b|||%an|||%ai"
    stdout, _, code = run_git([
        "log", f"--since={days}.days.ago",
        f"--pretty=format:{fmt}",
        "--reverse",
    ])
    if code != 0 or not stdout.strip():
        return []
    return _parse_log_output(stdout)


def get_tags() -> list[str]:
    """Get tags sorted by version (newest first)."""
    stdout, _, code = run_git(["tag", "--sort=-version:refname"])
    if code != 0 or not stdout.strip():
        return []
    return [t for t in stdout.strip().split("\n") if t]


def _parse_log_output(stdout: str) -> list[dict[str, str]]:
    """Parse git log output with ||| delimiter."""
    commits = []
    for line in stdout.strip().split("\n"):
        parts = line.split("|||")
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0][:8],
                "subject": parts[1],
                "body": parts[2],
                "author": parts[3],
                "date": parts[4].strip(),
            })
    return commits
