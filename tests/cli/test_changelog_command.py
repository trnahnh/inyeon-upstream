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
        "changelog": {
            "version": "3.0.0",
            "date": "2026-02-17",
            "sections": {
                "feat": ["Add session management", "Add pipeline"],
                "fix": ["Fix auth timeout"],
            },
            "summary": "Major release with new features.",
        },
        "reasoning": ["Grouped 3 commits", "Generated changelog"],
        "error": None,
    }


class TestChangelogCommand:

    @patch("cli.commands.changelog.is_git_repo")
    def test_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False

        result = runner.invoke(app, ["changelog", "--from", "v2.0.0"])

        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    @patch("cli.commands.changelog.get_commits_between")
    @patch("cli.commands.changelog.is_git_repo")
    def test_no_commits_found(self, mock_is_git, mock_commits, runner):
        mock_is_git.return_value = True
        mock_commits.return_value = []

        result = runner.invoke(app, ["changelog", "--from", "v2.0.0"])

        assert result.exit_code == 0
        assert "No commits found" in result.stdout

    @patch("cli.commands.changelog.get_tags")
    @patch("cli.commands.changelog.is_git_repo")
    def test_no_from_no_tags(self, mock_is_git, mock_tags, runner):
        mock_is_git.return_value = True
        mock_tags.return_value = []

        result = runner.invoke(app, ["changelog"])

        assert result.exit_code == 1
        assert "--from" in result.stdout or "--last" in result.stdout

    @patch("cli.commands.changelog.APIClient")
    @patch("cli.commands.changelog.get_commits_between")
    @patch("cli.commands.changelog.is_git_repo")
    def test_from_ref_mode(
        self, mock_is_git, mock_commits, mock_client_class,
        runner, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_commits.return_value = [
            {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev", "date": "2026-02-17"},
        ]

        mock_client = MagicMock()
        mock_client.generate_changelog.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["changelog", "--from", "v2.0.0", "--json"])

        assert result.exit_code == 0
        assert "changelog" in result.stdout
        mock_commits.assert_called_once_with("v2.0.0", "HEAD")

    @patch("cli.commands.changelog.APIClient")
    @patch("cli.commands.changelog.get_commits_since")
    @patch("cli.commands.changelog.is_git_repo")
    def test_last_days_mode(
        self, mock_is_git, mock_commits, mock_client_class,
        runner, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_commits.return_value = [
            {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev", "date": "2026-02-17"},
        ]

        mock_client = MagicMock()
        mock_client.generate_changelog.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["changelog", "--last", "7", "--json"])

        assert result.exit_code == 0
        mock_commits.assert_called_once_with(7)

    @patch("cli.commands.changelog.APIClient")
    @patch("cli.commands.changelog.get_commits_between")
    @patch("cli.commands.changelog.get_tags")
    @patch("cli.commands.changelog.is_git_repo")
    def test_auto_tag_mode(
        self, mock_is_git, mock_tags, mock_commits, mock_client_class,
        runner, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_tags.return_value = ["v2.0.0", "v1.0.0"]
        mock_commits.return_value = [
            {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev", "date": "2026-02-17"},
        ]

        mock_client = MagicMock()
        mock_client.generate_changelog.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["changelog", "--json"])

        assert result.exit_code == 0
        mock_commits.assert_called_once_with("v2.0.0", "HEAD")

    @patch("cli.commands.changelog.APIClient")
    @patch("cli.commands.changelog.get_commits_between")
    @patch("cli.commands.changelog.is_git_repo")
    def test_displays_changelog(
        self, mock_is_git, mock_commits, mock_client_class,
        runner, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_commits.return_value = [
            {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev", "date": "2026-02-17"},
        ]

        mock_client = MagicMock()
        mock_client.generate_changelog.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["changelog", "--from", "v2.0.0"])

        assert result.exit_code == 0
        assert "Changelog" in result.stdout
        assert "Features" in result.stdout

    @patch("cli.commands.changelog.APIClient")
    @patch("cli.commands.changelog.get_commits_between")
    @patch("cli.commands.changelog.is_git_repo")
    def test_handles_api_error(
        self, mock_is_git, mock_commits, mock_client_class, runner,
    ):
        from cli.api_client import APIError

        mock_is_git.return_value = True
        mock_commits.return_value = [
            {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev", "date": "2026-02-17"},
        ]

        mock_client = MagicMock()
        mock_client.generate_changelog.side_effect = APIError("Connection failed")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["changelog", "--from", "v2.0.0"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    @patch("cli.commands.changelog.APIClient")
    @patch("cli.commands.changelog.get_commits_between")
    @patch("cli.commands.changelog.is_git_repo")
    def test_handles_backend_error(
        self, mock_is_git, mock_commits, mock_client_class, runner,
    ):
        mock_is_git.return_value = True
        mock_commits.return_value = [
            {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev", "date": "2026-02-17"},
        ]

        mock_client = MagicMock()
        mock_client.generate_changelog.return_value = {
            "changelog": None,
            "reasoning": [],
            "error": "Generation failed",
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["changelog", "--from", "v2.0.0"])

        assert result.exit_code == 1
        assert "Generation failed" in result.stdout
