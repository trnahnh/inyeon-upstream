import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_api_response():
    return {
        "resolutions": [
            {
                "path": "greet.py",
                "resolved_content": 'def greet():\n    print("Hello")\n',
                "strategy": "merge",
                "explanation": "Merged both sides",
            },
        ],
        "reasoning": ["Parsed 1 file", "Resolved 1 conflict"],
        "error": None,
    }


class TestResolveCommand:

    @patch("cli.commands.resolve.is_git_repo")
    def test_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False

        result = runner.invoke(app, ["resolve", "--all"])

        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    @patch("cli.commands.resolve.is_git_repo")
    def test_requires_file_or_all(self, mock_is_git, runner):
        mock_is_git.return_value = True

        result = runner.invoke(app, ["resolve"])

        assert result.exit_code == 1
        assert "--file" in result.stdout or "--all" in result.stdout

    @patch("cli.commands.resolve.get_merge_conflicts")
    @patch("cli.commands.resolve.is_git_repo")
    def test_no_conflicts_found(self, mock_is_git, mock_conflicts, runner):
        mock_is_git.return_value = True
        mock_conflicts.return_value = []

        result = runner.invoke(app, ["resolve", "--all"])

        assert result.exit_code == 0
        assert "No merge conflicts" in result.stdout

    @patch("cli.commands.resolve.APIClient")
    @patch("cli.commands.resolve.get_theirs_version")
    @patch("cli.commands.resolve.get_ours_version")
    @patch("cli.commands.resolve.get_conflict_content")
    @patch("cli.commands.resolve.get_merge_conflicts")
    @patch("cli.commands.resolve.is_git_repo")
    def test_json_output(
        self, mock_is_git, mock_conflicts, mock_content, mock_ours, mock_theirs,
        mock_client_class, runner, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_conflicts.return_value = ["greet.py"]
        mock_content.return_value = "conflicted content"
        mock_ours.return_value = "ours"
        mock_theirs.return_value = "theirs"

        mock_client = MagicMock()
        mock_client.resolve_conflicts.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["resolve", "--all", "--json"])

        assert result.exit_code == 0
        assert "resolutions" in result.stdout
        assert "merge" in result.stdout

    @patch("cli.commands.resolve.APIClient")
    @patch("cli.commands.resolve.get_theirs_version")
    @patch("cli.commands.resolve.get_ours_version")
    @patch("cli.commands.resolve.get_conflict_content")
    @patch("cli.commands.resolve.is_git_repo")
    def test_single_file_mode(
        self, mock_is_git, mock_content, mock_ours, mock_theirs,
        mock_client_class, runner, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_content.return_value = "conflicted content"
        mock_ours.return_value = "ours"
        mock_theirs.return_value = "theirs"

        mock_client = MagicMock()
        mock_client.resolve_conflicts.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["resolve", "--file", "greet.py", "--json"])

        assert result.exit_code == 0
        mock_content.assert_called_once_with("greet.py")

    @patch("cli.commands.resolve.APIClient")
    @patch("cli.commands.resolve.get_theirs_version")
    @patch("cli.commands.resolve.get_ours_version")
    @patch("cli.commands.resolve.get_conflict_content")
    @patch("cli.commands.resolve.get_merge_conflicts")
    @patch("cli.commands.resolve.is_git_repo")
    def test_handles_api_error(
        self, mock_is_git, mock_conflicts, mock_content, mock_ours, mock_theirs,
        mock_client_class, runner,
    ):
        from cli.api_client import APIError

        mock_is_git.return_value = True
        mock_conflicts.return_value = ["greet.py"]
        mock_content.return_value = "conflicted"
        mock_ours.return_value = "ours"
        mock_theirs.return_value = "theirs"

        mock_client = MagicMock()
        mock_client.resolve_conflicts.side_effect = APIError("Connection failed")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["resolve", "--all"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    @patch("cli.commands.resolve.APIClient")
    @patch("cli.commands.resolve.get_theirs_version")
    @patch("cli.commands.resolve.get_ours_version")
    @patch("cli.commands.resolve.get_conflict_content")
    @patch("cli.commands.resolve.get_merge_conflicts")
    @patch("cli.commands.resolve.is_git_repo")
    def test_handles_backend_error(
        self, mock_is_git, mock_conflicts, mock_content, mock_ours, mock_theirs,
        mock_client_class, runner,
    ):
        mock_is_git.return_value = True
        mock_conflicts.return_value = ["greet.py"]
        mock_content.return_value = "conflicted"
        mock_ours.return_value = "ours"
        mock_theirs.return_value = "theirs"

        mock_client = MagicMock()
        mock_client.resolve_conflicts.return_value = {
            "resolutions": [],
            "reasoning": [],
            "error": "No conflict markers found",
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["resolve", "--all"])

        assert result.exit_code == 1
        assert "No conflict markers" in result.stdout
