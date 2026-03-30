from unittest.mock import AsyncMock

from backend.main import app
from backend.core.dependencies import get_llm_provider
from backend.utils.cost import clear_cache


CONFLICT_CONTENT = """def greet():
<<<<<<< HEAD
    print("Hello from ours")
=======
    print("Hello from theirs")
>>>>>>> branch
"""


class TestConflictRouter:

    def setup_method(self):
        clear_cache()
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_resolve_endpoint_exists(self, client):
        response = client.post("/api/v1/agent/resolve", json={"conflicts": [{"path": "a.py", "content": "x"}]})
        assert response.status_code != 404

    def test_resolve_returns_response(self, client):
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value={
                "resolved_content": 'def greet():\n    print("Hello")\n',
                "strategy": "merge",
                "explanation": "Merged both",
            }
        )
        app.dependency_overrides[get_llm_provider] = lambda: mock_llm

        response = client.post(
            "/api/v1/agent/resolve",
            json={
                "conflicts": [
                    {
                        "path": "greet.py",
                        "content": CONFLICT_CONTENT,
                        "ours": "ours content",
                        "theirs": "theirs content",
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "resolutions" in data
        assert "reasoning" in data

    def test_resolve_empty_conflicts_rejected(self, client):
        response = client.post("/api/v1/agent/resolve", json={"conflicts": []})
        assert response.status_code == 422

    def test_resolve_missing_conflicts_rejected(self, client):
        response = client.post("/api/v1/agent/resolve", json={})
        assert response.status_code == 422
