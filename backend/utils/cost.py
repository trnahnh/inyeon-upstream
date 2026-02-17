import hashlib
from typing import Any


DEFAULT_MAX_DIFF_CHARS = 30000


def truncate_diff(diff: str, max_chars: int = DEFAULT_MAX_DIFF_CHARS) -> str:
    """Truncate a diff to fit within token budget.

    Keeps file headers and first hunks, drops remaining hunks from large files.
    """
    if len(diff) <= max_chars:
        return diff

    sections = diff.split("diff --git ")
    parts: list[str] = []
    remaining = max_chars

    for section in sections:
        if not section.strip():
            continue

        full = "diff --git " + section

        if len(full) <= remaining:
            parts.append(full)
            remaining -= len(full)
        else:
            lines = full.split("\n")
            header = "\n".join(lines[:4]) + "\n"
            if len(header) <= remaining:
                parts.append(header)
                remaining -= len(header)

    return "".join(parts)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English/code)."""
    return len(text) // 4


_cache: dict[str, Any] = {}
_CACHE_MAX_SIZE = 100


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def get_cached(prompt: str) -> dict[str, Any] | None:
    """Return cached LLM response if available."""
    return _cache.get(_cache_key(prompt))


def set_cached(prompt: str, response: dict[str, Any]) -> None:
    """Cache an LLM response with LRU eviction."""
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest = next(iter(_cache))
        del _cache[oldest]
    _cache[_cache_key(prompt)] = response


def clear_cache() -> None:
    """Clear all cached responses."""
    _cache.clear()
