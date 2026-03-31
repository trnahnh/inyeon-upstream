import hashlib
import time
from typing import Any


DEFAULT_MAX_DIFF_CHARS = 30000
_CACHE_MAX_SIZE = 100
_CACHE_TTL_SECONDS = 300


def truncate_diff(diff: str, max_chars: int = DEFAULT_MAX_DIFF_CHARS) -> str:
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
    return len(text) // 4


_cache: dict[str, tuple[float, Any]] = {}


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def get_cached(prompt: str) -> dict[str, Any] | None:
    key = _cache_key(prompt)
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return value


def set_cached(prompt: str, response: dict[str, Any]) -> None:
    now = time.time()
    # Evict expired entries first
    expired = [k for k, (ts, _) in _cache.items() if now - ts > _CACHE_TTL_SECONDS]
    for k in expired:
        del _cache[k]
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]
    _cache[_cache_key(prompt)] = (now, response)


def clear_cache() -> None:
    _cache.clear()
