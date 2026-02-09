import pytest
from backend.diff import DiffParser, ParsedDiff, FileChangeType, LineType


@pytest.fixture
def parser():
    return DiffParser()


@pytest.fixture
def simple_diff():
    return """diff --git a/hello.py b/hello.py
index 1234567..abcdefg 100644
--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
+    return True
     pass
"""


@pytest.fixture
def multi_file_diff():
    return """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,2 +1,3 @@
 def main():
+    print("Starting")
     pass
diff --git a/tests/test_main.py b/tests/test_main.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/tests/test_main.py
@@ -0,0 +1,5 @@
+import pytest
+
+def test_main():
+    assert True
+
"""


@pytest.fixture
def deleted_file_diff():
    return """diff --git a/old_file.py b/old_file.py
deleted file mode 100644
index 1234567..0000000
--- a/old_file.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    pass
-
"""


class TestDiffParser:

    def test_parse_empty_diff(self, parser):
        result = parser.parse("")
        assert isinstance(result, ParsedDiff)
        assert len(result.files) == 0
        assert result.total_added == 0
        assert result.total_removed == 0

    def test_parse_whitespace_diff(self, parser):
        result = parser.parse("   \n\n  ")
        assert len(result.files) == 0

    def test_parse_single_file(self, parser, simple_diff):
        result = parser.parse(simple_diff)

        assert len(result.files) == 1
        assert result.files[0].path == "hello.py"
        assert result.files[0].change_type == FileChangeType.MODIFIED
        assert len(result.files[0].hunks) == 1

    def test_parse_hunk_content(self, parser, simple_diff):
        result = parser.parse(simple_diff)
        hunk = result.files[0].hunks[0]

        assert hunk.id == "hello.py:0"
        assert hunk.added_count == 2
        assert hunk.removed_count == 1
        assert len(hunk.lines) > 0

    def test_parse_line_types(self, parser, simple_diff):
        result = parser.parse(simple_diff)
        lines = result.files[0].hunks[0].lines

        line_types = [line.line_type for line in lines]
        assert LineType.ADDED in line_types
        assert LineType.REMOVED in line_types
        assert LineType.CONTEXT in line_types

    def test_parse_multiple_files(self, parser, multi_file_diff):
        result = parser.parse(multi_file_diff)

        assert len(result.files) == 2
        paths = [f.path for f in result.files]
        assert "src/main.py" in paths
        assert "tests/test_main.py" in paths

    def test_parse_new_file(self, parser, multi_file_diff):
        result = parser.parse(multi_file_diff)

        test_file = next(f for f in result.files if "test_main" in f.path)
        assert test_file.change_type == FileChangeType.ADDED

    def test_parse_deleted_file(self, parser, deleted_file_diff):
        result = parser.parse(deleted_file_diff)

        assert len(result.files) == 1
        assert result.files[0].change_type == FileChangeType.DELETED
        assert result.files[0].path == "old_file.py"

    def test_parse_total_counts(self, parser, multi_file_diff):
        result = parser.parse(multi_file_diff)

        assert result.total_added > 0
        assert result.total_removed == 0

    def test_get_all_hunks(self, parser, multi_file_diff):
        result = parser.parse(multi_file_diff)
        all_hunks = result.get_all_hunks()

        assert len(all_hunks) == 2
        for file, hunk in all_hunks:
            assert file.path in ["src/main.py", "tests/test_main.py"]
            assert hunk.id.startswith(file.path)

    def test_file_directory_property(self, parser, multi_file_diff):
        result = parser.parse(multi_file_diff)

        src_file = next(f for f in result.files if f.path == "src/main.py")
        assert src_file.directory == "src"

        test_file = next(f for f in result.files if "test_main" in f.path)
        assert test_file.directory == "tests"

    def test_file_extension_property(self, parser, simple_diff):
        result = parser.parse(simple_diff)

        assert result.files[0].extension == ".py"

    def test_hunk_content_property(self, parser, simple_diff):
        result = parser.parse(simple_diff)
        hunk = result.files[0].hunks[0]

        assert isinstance(hunk.content, str)
        assert len(hunk.content) > 0
