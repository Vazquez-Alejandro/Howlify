from __future__ import annotations

import os
import time
from typing import Any, Optional

TTL_DEFAULT = int(os.getenv("CACHE_TTL_SECONDS", "300"))
_cache: dict[str, tuple[float, Any]] = {}


def cached(key: str, ttl: Optional[int] = None) -> Any:
    ttl = ttl if ttl is not None else TTL_DEFAULT
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < ttl:
        return entry[1]
    return None


def set_cache(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


def clear_cache() -> None:
    _cache.clear()


def cache_key(url: str, keyword: str = "", max_price: int = 0) -> str:
    return f"{url}|{keyword}|{max_price}"
