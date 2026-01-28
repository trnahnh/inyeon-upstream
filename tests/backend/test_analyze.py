import pytest


def test_analyze_empty_diff(client):
    """Test that empty diff returns 422 validation error."""
    response = client.post("/api/v1/analyze", json={"diff": ""})

    assert response.status_code == 422  # Validation error


def test_analyze_missing_diff(client):
    """Test that missing diff field returns 422."""
    response = client.post("/api/v1/analyze", json={})

    assert response.status_code == 422


def test_analyze_diff_too_large(client, large_diff):
    """Test that oversized diff returns 422."""
    response = client.post("/api/v1/analyze", json={"diff": large_diff})

    assert response.status_code == 422


def test_analyze_valid_diff_structure(client, sample_diff):
    """
    Test that valid diff returns correct response structure.

    Note: This test requires Ollama to be running.
    Skip if Ollama is not available.
    """
    response = client.post("/api/v1/analyze", json={"diff": sample_diff})

    # If Ollama is not running, we get 503
    if response.status_code == 503:
        pytest.skip("Ollama not available")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "summary" in data
    assert "impact" in data
    assert "categories" in data
    assert "files_changed" in data
    assert data["impact"] in ["low", "medium", "high"]
