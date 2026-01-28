import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_diff():
    """Sample git diff for testing."""
    return """diff --git a/hello.py b/hello.py
index 1234567..abcdefg 100644
--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
def greet(name):
-    print("Hello")
+    print(f"Hello, {name}!")
+    return name
"""


@pytest.fixture
def large_diff():
    """Diff that exceeds max size limit."""
    return "x" * 60000
