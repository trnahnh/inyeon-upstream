import json
from collections.abc import Iterator

import httpx

from cli.config import settings


class APIError(Exception):
    pass


class APIClient:

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        api_key: str | None = None,
        provider: str | None = None,
    ):
        self.base_url = base_url or settings.api_url
        self.timeout = timeout or settings.timeout
        self._api_key = api_key or settings.api_key
        self._provider = provider or settings.llm_provider
        self._max_diff = settings.max_diff_chars

    def _truncate_diff(self, diff: str) -> str:
        if len(diff) <= self._max_diff:
            return diff
        return diff[: self._max_diff]

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if self._provider:
            headers["X-LLM-Provider"] = self._provider

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise APIError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = e.response.text
            raise APIError(f"API error ({e.response.status_code}): {detail}")
        except httpx.ConnectError:
            raise APIError(f"Cannot connect to backend at {self.base_url}")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Request failed: {e}")

    def _stream_request(self, endpoint: str, **kwargs) -> Iterator[dict]:
        """Stream SSE events from an endpoint."""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if self._provider:
            headers["X-LLM-Provider"] = self._provider

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                with client.stream(
                    "POST", url, headers=headers, **kwargs
                ) as response:
                    response.raise_for_status()
                    buffer = ""
                    for chunk in response.iter_text():
                        buffer += chunk
                        while "\n\n" in buffer:
                            event_text, buffer = buffer.split("\n\n", 1)
                            data_line = None
                            for line in event_text.strip().split("\n"):
                                if line.startswith("data: "):
                                    data_line = line[6:]
                            if data_line:
                                yield json.loads(data_line)
        except httpx.TimeoutException:
            raise APIError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = e.response.text
            raise APIError(f"API error ({e.response.status_code}): {detail}")
        except httpx.ConnectError:
            raise APIError(f"Cannot connect to backend at {self.base_url}")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Streaming request failed: {e}")

    def generate_commit_stream(
        self, diff: str, repo_path: str = ".", issue_ref: str | None = None
    ) -> Iterator[dict]:
        payload: dict = {"diff": self._truncate_diff(diff), "repo_path": repo_path}
        if issue_ref:
            payload["issue_ref"] = issue_ref
        yield from self._stream_request("/api/v1/agent/stream/commit", json=payload)

    def review_stream(self, diff: str, repo_path: str = ".") -> Iterator[dict]:
        yield from self._stream_request(
            "/api/v1/agent/stream/review",
            json={"diff": self._truncate_diff(diff), "repo_path": repo_path},
        )

    def generate_pr_stream(
        self,
        diff: str,
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
    ) -> Iterator[dict]:
        payload = {
            "diff": self._truncate_diff(diff),
            "commits": commits or [],
            "branch_name": branch_name,
            "base_branch": base_branch,
        }
        yield from self._stream_request("/api/v1/agent/stream/pr", json=payload)

    def split_diff_stream(
        self, diff: str, strategy: str = "hybrid", repo_path: str = "."
    ) -> Iterator[dict]:
        payload = {
            "diff": self._truncate_diff(diff),
            "strategy": strategy,
            "repo_path": repo_path,
        }
        yield from self._stream_request("/api/v1/agent/stream/split", json=payload)

    def resolve_conflicts_stream(
        self, conflicts: list[dict[str, str]]
    ) -> Iterator[dict]:
        yield from self._stream_request(
            "/api/v1/agent/stream/resolve", json={"conflicts": conflicts}
        )

    def generate_changelog_stream(
        self,
        commits: list[dict[str, str]],
        from_ref: str = "",
        to_ref: str = "HEAD",
    ) -> Iterator[dict]:
        payload = {"commits": commits, "from_ref": from_ref, "to_ref": to_ref}
        yield from self._stream_request("/api/v1/agent/stream/changelog", json=payload)

    def health_check(self) -> dict:
        return self._request("GET", "/health")

    def list_providers(self) -> dict:
        return self._request("GET", "/providers")

    def analyze(self, diff: str, context: str | None = None) -> dict:
        payload: dict = {"diff": self._truncate_diff(diff)}
        if context:
            payload["context"] = context
        return self._request("POST", "/api/v1/analyze", json=payload)

    def generate_commit(self, diff: str, issue_ref: str | None = None) -> dict:
        payload: dict = {"diff": self._truncate_diff(diff)}
        if issue_ref:
            payload["issue_ref"] = issue_ref
        return self._request("POST", "/api/v1/generate-commit", json=payload)

    def run_agent(self, diff: str, repo_path: str = ".", verbose: bool = False) -> dict:
        payload = {"diff": self._truncate_diff(diff), "repo_path": repo_path, "verbose": verbose}
        return self._request("POST", "/api/v1/agent/run", json=payload)

    def review(self, diff: str) -> dict:
        payload = {"diff": self._truncate_diff(diff)}
        return self._request("POST", "/api/v1/agent/review", json=payload)

    def rag_index(self, repo_id: str, files: dict[str, str]) -> dict:
        payload = {"repo_id": repo_id, "files": files}
        return self._request("POST", "/api/v1/rag/index", json=payload)

    def rag_search(self, repo_id: str, query: str, n_results: int = 5) -> dict:
        payload = {"repo_id": repo_id, "query": query, "n_results": n_results}
        return self._request("POST", "/api/v1/rag/search", json=payload)

    def rag_stats(self, repo_id: str) -> dict:
        payload = {"repo_id": repo_id}
        return self._request("POST", "/api/v1/rag/stats", json=payload)

    def rag_clear(self, repo_id: str) -> dict:
        payload = {"repo_id": repo_id}
        return self._request("POST", "/api/v1/rag/clear", json=payload)

    def generate_pr(
        self,
        diff: str,
        commits: list[dict[str, str]] | None = None,
        branch_name: str = "",
        base_branch: str = "main",
    ) -> dict:
        payload = {
            "diff": self._truncate_diff(diff),
            "commits": commits or [],
            "branch_name": branch_name,
            "base_branch": base_branch,
        }
        return self._request("POST", "/api/v1/agent/pr", json=payload)

    def split_diff(
        self,
        diff: str,
        strategy: str = "hybrid",
        repo_path: str = ".",
    ) -> dict:
        payload = {
            "diff": self._truncate_diff(diff),
            "strategy": strategy,
            "repo_path": repo_path,
        }
        return self._request("POST", "/api/v1/agent/split", json=payload)

    def resolve_conflicts(self, conflicts: list[dict[str, str]]) -> dict:
        payload = {"conflicts": conflicts}
        return self._request("POST", "/api/v1/agent/resolve", json=payload)

    def generate_changelog(
        self,
        commits: list[dict[str, str]],
        from_ref: str = "",
        to_ref: str = "HEAD",
    ) -> dict:
        payload = {
            "commits": commits,
            "from_ref": from_ref,
            "to_ref": to_ref,
        }
        return self._request("POST", "/api/v1/agent/changelog", json=payload)
