from unittest.mock import AsyncMock

from backend.main import app
from backend.core.dependencies import get_llm_from_request
from backend.utils.cost import clear_cache


class TestChangelogRouter:

    def setup_method(self):
        clear_cache()
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_changelog_endpoint_exists(self, client):
        response = client.post(
            "/api/v1/agent/changelog",
            json={"commits": [{"hash": "abc", "subject": "feat: test", "body": "", "author": "dev"}]},
        )
        assert response.status_code != 404

    def test_changelog_returns_response(self, client):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value={
                "version": "3.0.0",
                "date": "2026-02-17",
                "sections": {"feat": ["New feature"]},
                "summary": "Release summary.",
            }
        )
        app.dependency_overrides[get_llm_from_request] = lambda: mock_llm

        response = client.post(
            "/api/v1/agent/changelog",
            json={
                "commits": [
                    {"hash": "abc", "subject": "feat: test", "body": "", "author": "dev"},
                ],
                "from_ref": "v2.0.0",
                "to_ref": "HEAD",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "changelog" in data
        assert "reasoning" in data

    def test_changelog_empty_commits_rejected(self, client):
        response = client.post("/api/v1/agent/changelog", json={"commits": []})
        assert response.status_code == 422

    def test_changelog_missing_commits_rejected(self, client):
        response = client.post("/api/v1/agent/changelog", json={})
        assert response.status_code == 422
