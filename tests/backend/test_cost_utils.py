from backend.utils.cost import (
    truncate_diff,
    estimate_tokens,
    get_cached,
    set_cached,
    clear_cache,
)


class TestTruncateDiff:

    def test_no_truncation_under_limit(self):
        diff = "diff --git a/f.py b/f.py\nsmall change\n"
        result = truncate_diff(diff, max_chars=1000)
        assert result == diff

    def test_truncates_at_limit(self):
        section = "diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n"
        diff = section * 100
        result = truncate_diff(diff, max_chars=500)
        assert len(result) <= 500 + len(section)

    def test_preserves_file_headers(self):
        diff = (
            "diff --git a/small.py b/small.py\n"
            "index abc..def 100644\n"
            "--- a/small.py\n"
            "+++ b/small.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+line\n"
        )
        big = diff + "diff --git a/big.py b/big.py\n" + "x" * 50000
        result = truncate_diff(big, max_chars=200)
        assert "diff --git a/small.py" in result

    def test_empty_diff(self):
        assert truncate_diff("") == ""

    def test_exact_limit(self):
        diff = "diff --git a/f.py b/f.py\nok\n"
        result = truncate_diff(diff, max_chars=len(diff))
        assert result == diff


class TestEstimateTokens:

    def test_basic_estimate(self):
        assert estimate_tokens("abcd") == 1

    def test_longer_text(self):
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_empty(self):
        assert estimate_tokens("") == 0


class TestResponseCache:

    def setup_method(self):
        clear_cache()

    def test_cache_miss_returns_none(self):
        assert get_cached("unknown prompt") is None

    def test_cache_hit_returns_response(self):
        set_cached("my prompt", {"text": "result"})
        assert get_cached("my prompt") == {"text": "result"}

    def test_different_prompts_different_keys(self):
        set_cached("prompt A", {"a": 1})
        set_cached("prompt B", {"b": 2})
        assert get_cached("prompt A") == {"a": 1}
        assert get_cached("prompt B") == {"b": 2}

    def test_cache_eviction_at_max_size(self):
        for i in range(105):
            set_cached(f"prompt-{i}", {"i": i})
        # First few should have been evicted
        assert get_cached("prompt-0") is None
        # Recent ones should still exist
        assert get_cached("prompt-104") == {"i": 104}

    def test_clear_cache(self):
        set_cached("prompt", {"data": True})
        clear_cache()
        assert get_cached("prompt") is None
