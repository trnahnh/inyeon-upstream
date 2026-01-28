import subprocess
from unittest.mock import patch, MagicMock

from cli.git_utils import (
    run_git,
    is_git_repo,
    get_staged_diff,
    get_current_branch,
    GitError,
)


def test_run_git_success():
    """Test run_git returns stdout on success."""
    stdout, stderr, code = run_git(["--version"])

    assert code == 0
    assert "git version" in stdout


def test_run_git_check_raises_on_failure():
    """Test run_git raises GitError when check=True and command fails."""
    import pytest

    with pytest.raises(GitError):
        run_git(["nonexistent-command"], check=True)


def test_is_git_repo_in_repo():
    """Test is_git_repo returns True in a git repository."""
    # This test runs in the project directory which is a git repo
    assert is_git_repo() is True


@patch("cli.git_utils.run_git")
def test_is_git_repo_not_in_repo(mock_run_git):
    """Test is_git_repo returns False outside a git repository."""
    mock_run_git.return_value = ("", "not a git repository", 128)

    assert is_git_repo() is False


@patch("cli.git_utils.run_git")
def test_get_staged_diff(mock_run_git):
    """Test get_staged_diff returns diff content."""
    expected_diff = "diff --git a/file.py b/file.py\n+new line"
    mock_run_git.return_value = (expected_diff, "", 0)

    result = get_staged_diff()

    assert result == expected_diff
    mock_run_git.assert_called_once_with(["diff", "--cached"])


@patch("cli.git_utils.run_git")
def test_get_current_branch(mock_run_git):
    """Test get_current_branch returns branch name."""
    mock_run_git.return_value = ("main\n", "", 0)

    result = get_current_branch()

    assert result == "main"
