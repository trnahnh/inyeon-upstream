import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from cli.main import app
from cli.pipeline import PipelineResult


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
def pipeline_result():
    result = PipelineResult()
    result.steps_completed = ["commit", "pr"]
    result.steps_skipped = ["split", "review"]
    result.commit_message = "feat: add print statement"
    result.pr_description = {"title": "feat: update", "summary": "Updates code."}
    return result


@pytest.fixture
def split_pipeline_result():
    result = PipelineResult()
    result.steps_completed = ["split", "pr"]
    result.steps_skipped = ["commit", "review"]
    result.splits = [
        {"group_id": "g1", "files": ["main.py"], "commit_message": "feat: add print", "commit_type": "feat"},
        {"group_id": "g2", "files": ["utils.py"], "commit_message": "feat: add helper", "commit_type": "feat"},
    ]
    result.pr_description = {"title": "feat: update", "summary": "Updates code."}
    return result


class TestAutoCommand:

    @patch("cli.commands.auto.is_git_repo")
    def test_not_git_repo(self, mock_is_git, runner):
        mock_is_git.return_value = False

        result = runner.invoke(app, ["auto", "--staged"])

        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    @patch("cli.commands.auto.is_git_repo")
    def test_requires_staged_or_all(self, mock_is_git, runner):
        mock_is_git.return_value = True

        result = runner.invoke(app, ["auto"])

        assert result.exit_code == 1
        assert "--staged" in result.stdout or "--all" in result.stdout

    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_no_changes(self, mock_diff, mock_is_git, mock_branch, runner):
        mock_is_git.return_value = True
        mock_diff.return_value = ""
        mock_branch.return_value = "main"

        result = runner.invoke(app, ["auto", "--staged"])

        assert result.exit_code == 0
        assert "No changes" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_dry_run_no_commits(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff, pipeline_result,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = pipeline_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged", "--dry-run"])

        assert result.exit_code == 0
        assert "--dry-run" in result.stdout
        assert "Pipeline Result" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_json_output(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff, pipeline_result,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = pipeline_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged", "--json"])

        assert result.exit_code == 0
        assert "steps_completed" in result.stdout
        assert "commit_message" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_pipeline_error(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        error_result = PipelineResult()
        error_result.error = "Split failed: timeout"
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = error_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged"])

        assert result.exit_code == 1
        assert "Split failed" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_all_diff")
    def test_all_flag(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff, pipeline_result,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = pipeline_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--all", "--dry-run"])

        assert result.exit_code == 0
        mock_diff.assert_called_once()

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_displays_commit_message(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff, pipeline_result,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = pipeline_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged", "--dry-run"])

        assert "feat: add print statement" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_displays_splits(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff, split_pipeline_result,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = split_pipeline_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged", "--dry-run"])

        assert "feat: add print" in result.stdout
        assert "feat: add helper" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_displays_pr_title(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff, pipeline_result,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = pipeline_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged", "--dry-run"])

        assert "feat: update" in result.stdout

    @patch("cli.commands.auto.Pipeline")
    @patch("cli.commands.auto.get_branch_commits")
    @patch("cli.commands.auto.get_current_branch")
    @patch("cli.commands.auto.is_git_repo")
    @patch("cli.commands.auto.get_staged_diff")
    def test_json_error_exit_code(
        self, mock_diff, mock_is_git, mock_branch, mock_commits, mock_pipeline_class,
        runner, sample_diff,
    ):
        mock_is_git.return_value = True
        mock_diff.return_value = sample_diff
        mock_branch.return_value = "feature/test"
        mock_commits.return_value = []

        error_result = PipelineResult()
        error_result.error = "Failed"
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = error_result
        mock_pipeline_class.return_value = mock_pipeline

        result = runner.invoke(app, ["auto", "--staged", "--json"])

        assert result.exit_code == 1
        assert "error" in result.stdout
