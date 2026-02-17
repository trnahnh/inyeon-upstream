from unittest.mock import MagicMock

from cli.api_client import APIError
from cli.pipeline import Pipeline, PipelineResult


SMALL_DIFF = """diff --git a/main.py b/main.py
index 1234567..abcdefg 100644
--- a/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
 def main():
+    print("Hello")
     pass
"""

MULTI_FILE_DIFF = """diff --git a/main.py b/main.py
index 1234567..abcdefg 100644
--- a/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
 def main():
+    print("Hello")
     pass
diff --git a/utils.py b/utils.py
index 1234567..abcdefg 100644
--- a/utils.py
+++ b/utils.py
@@ -1,2 +1,3 @@
 def helper():
+    return True
     pass
"""

LARGE_DIFF = "x" * 600


def _make_client(**overrides) -> MagicMock:
    client = MagicMock()
    client.split_diff.return_value = {
        "splits": [
            {"group_id": "g1", "files": ["main.py"], "commit_message": "feat: add print", "commit_type": "feat", "hunk_count": 1},
            {"group_id": "g2", "files": ["utils.py"], "commit_message": "feat: add helper", "commit_type": "feat", "hunk_count": 1},
        ],
        "total_groups": 2,
        "reasoning": [],
        "error": None,
    }
    client.generate_commit.return_value = {"message": "feat: add print statement", "type": "feat", "scope": None}
    client.review.return_value = {
        "review": {"quality_score": 8, "summary": "Good", "issues": [], "positives": [], "suggestions": []},
    }
    client.generate_pr.return_value = {
        "pr_description": {"title": "feat: update", "summary": "Updates code.", "changes": [], "testing": "", "breaking_changes": []},
        "reasoning": [],
        "error": None,
    }
    for key, val in overrides.items():
        setattr(client, key, val)
    return client


class TestPipelineShortCircuits:

    def test_skip_split_single_file(self):
        client = _make_client()
        result = Pipeline(client).run(SMALL_DIFF, skip_review=True, skip_pr=True)

        assert "split" in result.steps_skipped
        assert "commit" in result.steps_completed
        client.split_diff.assert_not_called()
        client.generate_commit.assert_called_once()

    def test_run_split_multi_file(self):
        client = _make_client()
        result = Pipeline(client).run(MULTI_FILE_DIFF, skip_review=True, skip_pr=True)

        assert "split" in result.steps_completed
        assert "commit" in result.steps_skipped
        assert result.splits is not None
        assert len(result.splits) == 2
        client.generate_commit.assert_not_called()

    def test_skip_review_small_diff(self):
        client = _make_client()
        result = Pipeline(client).run(SMALL_DIFF, skip_pr=True)

        assert "review" in result.steps_skipped
        client.review.assert_not_called()

    def test_run_review_large_diff(self):
        client = _make_client()
        result = Pipeline(client).run(LARGE_DIFF, skip_pr=True)

        assert "review" in result.steps_completed
        client.review.assert_called_once()

    def test_skip_review_flag(self):
        client = _make_client()
        result = Pipeline(client).run(LARGE_DIFF, skip_review=True, skip_pr=True)

        assert "review" in result.steps_skipped
        client.review.assert_not_called()

    def test_skip_pr_flag(self):
        client = _make_client()
        result = Pipeline(client).run(SMALL_DIFF, skip_pr=True)

        assert "pr" in result.steps_skipped
        client.generate_pr.assert_not_called()

    def test_run_pr(self):
        client = _make_client()
        result = Pipeline(client).run(
            SMALL_DIFF,
            commits=[{"hash": "abc", "subject": "feat: test", "body": "", "author": "dev"}],
            branch_name="feature/test",
            base_branch="main",
        )

        assert "pr" in result.steps_completed
        assert result.pr_description is not None
        client.generate_pr.assert_called_once()


class TestPipelineFullRun:

    def test_full_run_single_file(self):
        client = _make_client()
        result = Pipeline(client).run(LARGE_DIFF)

        assert "commit" in result.steps_completed
        assert "review" in result.steps_completed
        assert "pr" in result.steps_completed
        assert result.error is None

    def test_full_run_multi_file(self):
        large_multi = MULTI_FILE_DIFF + "x" * 600
        client = _make_client()
        result = Pipeline(client).run(large_multi)

        assert "split" in result.steps_completed
        assert "commit" in result.steps_skipped
        assert "review" in result.steps_completed
        assert "pr" in result.steps_completed
        assert result.error is None

    def test_result_dataclass_defaults(self):
        result = PipelineResult()
        assert result.steps_completed == []
        assert result.steps_skipped == []
        assert result.splits is None
        assert result.commit_message is None
        assert result.review is None
        assert result.pr_description is None
        assert result.error is None


class TestPipelineErrors:

    def test_split_api_error_stops_pipeline(self):
        client = _make_client(split_diff=MagicMock(side_effect=APIError("timeout")))
        result = Pipeline(client).run(MULTI_FILE_DIFF)

        assert result.error is not None
        assert "Split failed" in result.error
        client.generate_commit.assert_not_called()

    def test_split_backend_error_stops_pipeline(self):
        client = _make_client(
            split_diff=MagicMock(return_value={"splits": [], "error": "Clustering failed"}),
        )
        result = Pipeline(client).run(MULTI_FILE_DIFF)

        assert result.error is not None
        assert "Clustering failed" in result.error

    def test_commit_error_stops_pipeline(self):
        client = _make_client(generate_commit=MagicMock(side_effect=APIError("timeout")))
        result = Pipeline(client).run(SMALL_DIFF, skip_review=True, skip_pr=True)

        assert result.error is not None
        assert "Commit generation failed" in result.error

    def test_review_error_non_critical(self):
        client = _make_client(review=MagicMock(side_effect=APIError("timeout")))
        result = Pipeline(client).run(LARGE_DIFF, skip_pr=True)

        assert result.error is None
        assert "review" in result.steps_skipped

    def test_pr_error_non_critical(self):
        client = _make_client(generate_pr=MagicMock(side_effect=APIError("timeout")))
        result = Pipeline(client).run(SMALL_DIFF)

        assert result.error is None
        assert "pr" in result.steps_skipped

    def test_pr_backend_error_non_critical(self):
        client = _make_client(
            generate_pr=MagicMock(return_value={"pr_description": None, "error": "LLM error"}),
        )
        result = Pipeline(client).run(SMALL_DIFF)

        assert result.error is None
        assert "pr" in result.steps_skipped


class TestPipelineCustomThreshold:

    def test_threshold_3_skips_2_files(self):
        client = _make_client()
        result = Pipeline(client).run(MULTI_FILE_DIFF, split_threshold=3, skip_review=True, skip_pr=True)

        assert "split" in result.steps_skipped
        client.split_diff.assert_not_called()

    def test_threshold_1_splits_single_file(self):
        client = _make_client()
        result = Pipeline(client).run(SMALL_DIFF, split_threshold=1, skip_review=True, skip_pr=True)

        assert "split" in result.steps_completed
        client.split_diff.assert_called_once()
