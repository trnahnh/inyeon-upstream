import httpx

from cli.config import settings


class APIError(Exception):
    """Raised when API request fails."""

    pass


class APIClient:
    """Client for communicating with Inyeon Backend."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        self.base_url = base_url or settings.api_url
        self.timeout = timeout or settings.timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make HTTP request to backend."""
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise APIError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise APIError(f"API error ({e.response.status_code}): {detail}")
        except httpx.ConnectError:
            raise APIError(f"Cannot connect to backend at {self.base_url}")
        except Exception as e:
            raise APIError(f"Request failed: {e}")

    def health_check(self) -> dict:
        """Check backend health status."""
        return self._request("GET", "/health")

    def analyze(self, diff: str, context: str | None = None) -> dict:
        """Analyze a git diff."""
        payload = {"diff": diff}
        if context:
            payload["context"] = context
        return self._request("POST", "/api/v1/analyze", json=payload)

    def generate_commit(self, diff: str, issue_ref: str | None = None) -> dict:
        """Generate a commit message from a diff."""
        payload = {"diff": diff}
        if issue_ref:
            payload["issue_ref"] = issue_ref
        return self._request("POST", "/api/v1/generate-commit", json=payload)

    def run_agent(self, diff: str, repo_path: str = ".", verbose: bool = False) -> dict:
        """Run the git workflow agent."""
        payload = {"diff": diff, "repo_path": repo_path, "verbose": verbose}
        return self._request("POST", "/api/v1/agent/run", json=payload)

    def review(self, diff: str) -> dict:
        """Get code review feedback."""
        payload = {"diff": diff}
        return self._request("POST", "/api/v1/agent/review", json=payload)

    def rag_index(self, repo_id: str, files: dict[str, str]) -> dict:
        """Index files for RAG search."""
        payload = {"repo_id": repo_id, "files": files}
        return self._request("POST", "/api/v1/rag/index", json=payload)

    def rag_search(self, repo_id: str, query: str, n_results: int = 5) -> dict:
        """Search indexed code."""
        payload = {"repo_id": repo_id, "query": query, "n_results": n_results}
        return self._request("POST", "/api/v1/rag/search", json=payload)

    def rag_stats(self, repo_id: str) -> dict:
        """Get RAG index statistics."""
        payload = {"repo_id": repo_id}
        return self._request("POST", "/api/v1/rag/stats", json=payload)

    def rag_clear(self, repo_id: str) -> dict:
        """Clear RAG index for a repo."""
        payload = {"repo_id": repo_id}
        return self._request("POST", "/api/v1/rag/clear", json=payload)

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
