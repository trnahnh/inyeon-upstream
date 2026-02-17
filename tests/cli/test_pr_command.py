import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_diff():
    return """diff --git a/auth.py b/auth.py
index 1234567..abcdefg 100644
--- a/auth.py
+++ b/auth.py
@@ -1,3 +1,5 @@
 def login(user):
+    session = create_session(user)
+    return session
     pass
"""


@pytest.fixture
def mock_api_response():
    return {
        "pr_description": {
            "title": "feat(auth): add session management",
            "summary": "Adds session creation to login flow.",
            "changes": ["- Add session creation", "- Return session object"],
            "testing": "Run auth tests",
            "breaking_changes": [],
        },
        "reasoning": ["Analyzed branch", "Generated PR description"],
        "error": None,
    }


class TestPRCommand:

    @patch("cli.commands.pr.is_git_repo")
    def test_pr_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False

        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    def test_pr_no_changes(self, mock_diff, mock_is_git, mock_branch, runner):
        mock_is_git.return_value = True
        mock_diff.return_value = ""
        mock_branch.return_value = "feature/test"

        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 0
        assert "No changes" in result.stdout

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    @patch("cli.commands.pr.get_branch_commits")
    def test_pr_branch_mode(
        self, mock_commits, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_commits.return_value = [{"hash": "abc", "subject": "feat: test", "body": "", "author": "dev"}]
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 0
        assert "PR Title" in result.stdout
        assert "feat(auth): add session management" in result.stdout
        mock_diff.assert_called_once_with("main")
        mock_commits.assert_called_once_with("main")

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_staged_diff")
    def test_pr_staged_mode(
        self, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr", "--staged"])

        assert result.exit_code == 0
        mock_diff.assert_called_once()

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    @patch("cli.commands.pr.get_branch_commits")
    def test_pr_custom_base_branch(
        self, mock_commits, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_commits.return_value = []
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr", "--branch", "develop"])

        assert result.exit_code == 0
        mock_diff.assert_called_once_with("develop")
        mock_commits.assert_called_once_with("develop")

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    @patch("cli.commands.pr.get_branch_commits")
    def test_pr_json_output(
        self, mock_commits, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_commits.return_value = []
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr", "--json"])

        assert result.exit_code == 0
        assert "pr_description" in result.stdout
        assert "reasoning" in result.stdout

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    @patch("cli.commands.pr.get_branch_commits")
    def test_pr_handles_api_error(
        self, mock_commits, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff,
    ):
        from cli.api_client import APIError

        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_commits.return_value = []
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.side_effect = APIError("Connection failed")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    @patch("cli.commands.pr.get_branch_commits")
    def test_pr_handles_backend_error(
        self, mock_commits, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_commits.return_value = []
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.return_value = {
            "pr_description": None,
            "reasoning": [],
            "error": "LLM generation failed",
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 1
        assert "LLM generation failed" in result.stdout

    @patch("cli.commands.pr.APIClient")
    @patch("cli.commands.pr.get_current_branch")
    @patch("cli.commands.pr.is_git_repo")
    @patch("cli.commands.pr.get_branch_diff")
    @patch("cli.commands.pr.get_branch_commits")
    def test_pr_displays_all_sections(
        self, mock_commits, mock_diff, mock_is_git, mock_branch, mock_client_class,
        runner, sample_diff, mock_api_response,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_commits.return_value = []
        mock_branch.return_value = "feature/auth"

        mock_client = MagicMock()
        mock_client.generate_pr.return_value = mock_api_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 0
        assert "Summary" in result.stdout
        assert "Changes" in result.stdout
        assert "Testing" in result.stdout
