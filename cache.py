"""
cache.py – In-memory LRU cache for DevRelOS
Stores: recent intents, API mappings, session context, repeated query results
"""

import time
import asyncio
import os
from collections import OrderedDict
from typing import Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

_TTL       = int(os.getenv("CACHE_TTL_SECONDS", 300))
_MAX_SIZE  = int(os.getenv("MAX_CACHE_SIZE",    500))


class LRUCache:
    """Thread-safe async LRU cache with TTL support."""

    def __init__(self, max_size: int = _MAX_SIZE, ttl: int = _TTL):
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._max   = max_size
        self._ttl   = ttl
        self._lock  = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            value, ts = self._cache[key]
            if time.time() - ts > self._ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            if len(self._cache) > self._max:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)

    async def stats(self) -> dict:
        async with self._lock:
            now = time.time()
            live = sum(1 for _, (__, ts) in self._cache.items() if now - ts <= self._ttl)
            return {"total_keys": len(self._cache), "live_keys": live, "max_size": self._max, "ttl": self._ttl}


# ── Singleton Caches ──────────────────────────────────────────────────────────

intent_cache    = LRUCache(max_size=200, ttl=300)   # query → parsed intent
mapping_cache   = LRUCache(max_size=200, ttl=600)   # intent → API mapping
session_cache   = LRUCache(max_size=100, ttl=1800)  # session_id → session context
schema_cache    = LRUCache(max_size=50,  ttl=3600)  # provider → schema
response_cache  = LRUCache(max_size=100, ttl=120)   # exec hash → cached response


def _make_key(*parts) -> str:
    return ":".join(str(p) for p in parts)


# ── Helper Wrappers ───────────────────────────────────────────────────────────

async def get_cached_intent(query: str) -> Optional[Any]:
    return await intent_cache.get(_make_key("intent", query.lower().strip()))

async def set_cached_intent(query: str, intent: Any) -> None:
    await intent_cache.set(_make_key("intent", query.lower().strip()), intent)

async def get_cached_schema(provider: str) -> Optional[Any]:
    return await schema_cache.get(_make_key("schema", provider))

async def set_cached_schema(provider: str, schema: Any) -> None:
    await schema_cache.set(_make_key("schema", provider), schema)

async def get_cached_session(session_id: str) -> Optional[Any]:
    return await session_cache.get(_make_key("session", session_id))

async def set_cached_session(session_id: str, data: Any) -> None:
    await session_cache.set(_make_key("session", session_id), data)

async def get_cache_stats() -> dict:
    return {
        "intent":   await intent_cache.stats(),
        "mapping":  await mapping_cache.stats(),
        "session":  await session_cache.stats(),
        "schema":   await schema_cache.stats(),
        "response": await response_cache.stats(),
    }
