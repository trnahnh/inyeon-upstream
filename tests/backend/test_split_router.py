import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.main import app


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

    def test_split_endpoint_exists(self, client):
        response = client.post(
            "/api/v1/agent/split",
            json={"diff": "test", "strategy": "directory"},
        )
        assert response.status_code != 404

    @patch("backend.routers.split.get_llm")
    def test_split_returns_response(self, mock_get_llm, client, sample_diff, mock_llm):
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/api/v1/agent/split",
            json={"diff": sample_diff, "strategy": "directory"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "splits" in data
        assert "total_groups" in data
        assert "reasoning" in data

    @patch("backend.routers.split.get_llm")
    def test_split_empty_diff(self, mock_get_llm, client, mock_llm):
        mock_get_llm.return_value = mock_llm

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

    @patch("backend.routers.split.get_llm")
    def test_split_default_strategy(self, mock_get_llm, client, sample_diff, mock_llm):
        mock_get_llm.return_value = mock_llm

        response = client.post(
            "/api/v1/agent/split",
            json={"diff": sample_diff},
        )

        assert response.status_code == 200

    @patch("backend.routers.split.get_llm")
    def test_split_all_strategies(self, mock_get_llm, client, sample_diff, mock_llm):
        mock_get_llm.return_value = mock_llm

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
