import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_diff():
    return """diff --git a/main.py b/main.py
index 1234567..abcdefg 100644
--- a/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
 def main():
+    print("Hello")
     pass
"""


@pytest.fixture
def mock_api_response():
    return {
        "splits": [
            {
                "group_id": "dir-root",
                "files": ["main.py"],
                "hunk_count": 1,
                "commit_message": "feat: add print statement",
                "commit_type": "feat",
                "scope": None,
            }
        ],
        "total_groups": 1,
        "reasoning": ["Parsed diff: 1 file"],
        "error": None,
    }


class TestSplitCommand:

    @patch("cli.commands.split.is_git_repo")
    def test_split_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False

        result = runner.invoke(app, ["split", "--staged"])

        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_staged_diff")
    def test_split_no_changes(self, mock_diff, mock_is_git, runner):
        mock_is_git.return_value = True
        mock_diff.return_value = ""

        result = runner.invoke(app, ["split", "--staged"])

        assert result.exit_code == 0
        assert "No changes to split" in result.stdout

    @patch("cli.commands.split.is_git_repo")
    def test_split_requires_staged_or_all(self, mock_is_git, runner):
        mock_is_git.return_value = True

        result = runner.invoke(app, ["split"])

        assert result.exit_code == 1
        assert "--staged" in result.stdout or "--all" in result.stdout

    @patch("cli.commands.split.APIClient")
    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_staged_diff")
    def test_split_preview_mode(
        self, mock_diff, mock_is_git, mock_client_class, runner, sample_diff, mock_api_response
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff

        mock_client = MagicMock()
        mock_client.split_diff.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["split", "--staged", "--preview"])

        assert result.exit_code == 0
        assert "Split Result" in result.stdout
        assert "--preview" in result.stdout or "No commits created" in result.stdout

    @patch("cli.commands.split.APIClient")
    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_staged_diff")
    def test_split_json_output(
        self, mock_diff, mock_is_git, mock_client_class, runner, sample_diff, mock_api_response
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff

        mock_client = MagicMock()
        mock_client.split_diff.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["split", "--staged", "--json"])

        assert result.exit_code == 0
        assert "splits" in result.stdout
        assert "total_groups" in result.stdout

    @patch("cli.commands.split.APIClient")
    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_staged_diff")
    def test_split_displays_groups(
        self, mock_diff, mock_is_git, mock_client_class, runner, sample_diff, mock_api_response
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff

        mock_client = MagicMock()
        mock_client.split_diff.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["split", "--staged", "--preview"])

        assert "1 commit groups" in result.stdout or "Split Result" in result.stdout
        assert "main.py" in result.stdout

    @patch("cli.commands.split.APIClient")
    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_staged_diff")
    def test_split_handles_api_error(
        self, mock_diff, mock_is_git, mock_client_class, runner, sample_diff
    ):
        from cli.api_client import APIError

        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff

        mock_client = MagicMock()
        mock_client.split_diff.side_effect = APIError("Connection failed")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["split", "--staged", "--preview"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    @patch("cli.commands.split.APIClient")
    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_staged_diff")
    def test_split_handles_backend_error(
        self, mock_diff, mock_is_git, mock_client_class, runner, sample_diff
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff

        mock_client = MagicMock()
        mock_client.split_diff.return_value = {
            "splits": [],
            "total_groups": 0,
            "reasoning": [],
            "error": "Clustering failed",
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["split", "--staged", "--preview"])

        assert result.exit_code == 1
        assert "Clustering failed" in result.stdout

    @patch("cli.commands.split.APIClient")
    @patch("cli.commands.split.is_git_repo")
    @patch("cli.commands.split.get_all_diff")
    def test_split_all_flag(
        self, mock_diff, mock_is_git, mock_client_class, runner, sample_diff, mock_api_response
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff

        mock_client = MagicMock()
        mock_client.split_diff.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["split", "--all", "--preview"])

        assert result.exit_code == 0
        mock_diff.assert_called_once()
