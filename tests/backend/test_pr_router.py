from unittest.mock import patch, AsyncMock

from backend.utils.cost import clear_cache


class TestPRRouter:

    def setup_method(self):
        clear_cache()

    def test_pr_endpoint_exists(self, client):
        response = client.post("/api/v1/agent/pr", json={"diff": ""})
        assert response.status_code != 404

    @patch("backend.routers.pr.get_llm")
    def test_pr_returns_response(self, mock_get_llm, client, sample_diff):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value={
                "title": "feat: update",
                "summary": "Updates the code.",
                "changes": ["- Update code"],
                "testing": "Run tests",
                "breaking_changes": [],
            }
        )
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/api/v1/agent/pr",
            json={
                "diff": sample_diff,
                "commits": [{"hash": "abc", "subject": "feat: test", "body": "", "author": "dev"}],
                "branch_name": "feature/test",
                "base_branch": "main",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "pr_description" in data
        assert "reasoning" in data

    def test_pr_empty_diff_rejected(self, client):
        response = client.post("/api/v1/agent/pr", json={"diff": ""})
        assert response.status_code == 422

    def test_pr_missing_diff_rejected(self, client):
        response = client.post("/api/v1/agent/pr", json={})
        assert response.status_code == 422
