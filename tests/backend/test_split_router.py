import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.dependencies import get_llm_provider


@pytest.fixture
def client():
    return TestClient(app)


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
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value={
            "type": "feat",
            "scope": None,
            "subject": "add feature",
            "message": "feat: add feature",
        }
    )
    llm.is_healthy = AsyncMock(return_value=True)
    return llm


class TestSplitRouter:

    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_split_endpoint_exists(self, client):
        response = client.post(
            "/api/v1/agent/split",
            json={"diff": "test", "strategy": "directory"},
        )
        assert response.status_code != 404

    def test_split_returns_response(self, client, sample_diff, mock_llm):
        app.dependency_overrides[get_llm_provider] = lambda: mock_llm

        response = client.post(
            "/api/v1/agent/split",
            json={"diff": sample_diff, "strategy": "directory"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "splits" in data
        assert "total_groups" in data
        assert "reasoning" in data

    def test_split_empty_diff(self, client, mock_llm):
        app.dependency_overrides[get_llm_provider] = lambda: mock_llm

        response = client.post(
            "/api/v1/agent/split",
            json={"diff": "   ", "strategy": "directory"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_groups"] == 0

    def test_split_invalid_request(self, client):
        response = client.post(
            "/api/v1/agent/split",
            json={"strategy": "directory"},
        )
        assert response.status_code == 422

    def test_split_default_strategy(self, client, sample_diff, mock_llm):
        app.dependency_overrides[get_llm_provider] = lambda: mock_llm

        response = client.post(
            "/api/v1/agent/split",
            json={"diff": sample_diff},
        )

        assert response.status_code == 200

    def test_split_all_strategies(self, client, sample_diff, mock_llm):
        app.dependency_overrides[get_llm_provider] = lambda: mock_llm

        strategies = ["directory", "conventional", "hybrid"]
        for strategy in strategies:
            response = client.post(
                "/api/v1/agent/split",
                json={"diff": sample_diff, "strategy": strategy},
            )
            assert response.status_code == 200, f"Failed for strategy: {strategy}"

    def test_split_invalid_strategy(self, client, sample_diff):
        response = client.post(
            "/api/v1/agent/split",
            json={"diff": sample_diff, "strategy": "invalid"},
        )
        assert response.status_code == 422
