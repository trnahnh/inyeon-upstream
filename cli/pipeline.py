from dataclasses import dataclass, field

from cli.api_client import APIClient, APIError


@dataclass
class PipelineResult:
    steps_completed: list[str] = field(default_factory=list)
    steps_skipped: list[str] = field(default_factory=list)
    splits: list[dict] | None = None
    commit_message: str | None = None
    review: dict | None = None
    pr_description: dict | None = None
    error: str | None = None


class Pipeline:
    def __init__(self, client: APIClient):
        self.client = client

    def run(
        self,
        diff: str,
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
        skip_review: bool = False,
        skip_pr: bool = False,
        split_threshold: int = 2,
    ) -> PipelineResult:
        result = PipelineResult()

        self._step_split(result, diff, split_threshold)
        if result.error:
            return result

        self._step_commit(result, diff)
        if result.error:
            return result

        self._step_review(result, diff, skip_review)
        self._step_pr(result, diff, commits, branch_name, base_branch, skip_pr)

        return result

    def _step_split(
        self, result: PipelineResult, diff: str, threshold: int,
    ) -> None:
        file_count = diff.count("diff --git ")
        if file_count < threshold:
            result.steps_skipped.append("split")
            return

        try:
            resp = self.client.split_diff(diff)
        except APIError as e:
            result.error = f"Split failed: {e}"
            return

        if resp.get("error"):
            result.error = f"Split failed: {resp['error']}"
            return

        result.splits = resp.get("splits", [])
        result.steps_completed.append("split")

    def _step_commit(self, result: PipelineResult, diff: str) -> None:
        if result.splits:
            result.steps_skipped.append("commit")
            return

        try:
            resp = self.client.generate_commit(diff)
        except APIError as e:
            result.error = f"Commit generation failed: {e}"
            return

        result.commit_message = resp.get("message")
        result.steps_completed.append("commit")

    def _step_review(
        self, result: PipelineResult, diff: str, skip: bool,
    ) -> None:
        if skip or len(diff) < 500:
            result.steps_skipped.append("review")
            return

        try:
            resp = self.client.review(diff)
            result.review = resp.get("review")
            result.steps_completed.append("review")
        except APIError:
            result.steps_skipped.append("review")

    def _step_pr(
        self,
        result: PipelineResult,
        diff: str,
        commits: list[dict[str, str]] | None,
        branch_name: str,
        base_branch: str,
        skip: bool,
    ) -> None:
        if skip:
            result.steps_skipped.append("pr")
            return

        try:
            resp = self.client.generate_pr(
                diff=diff,
                commits=commits or [],
                branch_name=branch_name,
                base_branch=base_branch,
            )
            if resp.get("error"):
                result.steps_skipped.append("pr")
            else:
                result.pr_description = resp.get("pr_description")
                result.steps_completed.append("pr")
        except APIError:
            result.steps_skipped.append("pr")
