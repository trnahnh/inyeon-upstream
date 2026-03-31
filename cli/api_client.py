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

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if self._provider:
            headers["X-LLM-Provider"] = self._provider

        try:
            with httpx.Client(timeout=self.timeout) as client:
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

    def health_check(self) -> dict:
        return self._request("GET", "/health")

    def list_providers(self) -> dict:
        return self._request("GET", "/providers")

    def analyze(self, diff: str, context: str | None = None) -> dict:
        payload = {"diff": diff}
        if context:
            payload["context"] = context
        return self._request("POST", "/api/v1/analyze", json=payload)

    def generate_commit(self, diff: str, issue_ref: str | None = None) -> dict:
        payload = {"diff": diff}
        if issue_ref:
            payload["issue_ref"] = issue_ref
        return self._request("POST", "/api/v1/generate-commit", json=payload)

    def run_agent(self, diff: str, repo_path: str = ".", verbose: bool = False) -> dict:
        payload = {"diff": diff, "repo_path": repo_path, "verbose": verbose}
        return self._request("POST", "/api/v1/agent/run", json=payload)

    def review(self, diff: str) -> dict:
        payload = {"diff": diff}
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
            "diff": diff,
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
            "diff": diff,
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
