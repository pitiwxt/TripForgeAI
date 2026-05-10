"""
Thread-safe TTL + LRU cache for expensive API call results.
Prevents redundant Google Maps API calls during development and production.
"""

import time
import threading
from collections import OrderedDict
from typing import Any


class TTLCache:
    """
    A simple thread-safe LRU cache with TTL (time-to-live) expiration.
    
    - Keys are evicted after `ttl_seconds` regardless of access.
    - When capacity is reached, the least-recently-used key is evicted.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 86400):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value. Returns None if missing or expired."""
        with self._lock:
            if key not in self._cache:
                return None
            value, timestamp = self._cache[key]
            if time.time() - timestamp > self._ttl:
                # Expired — evict
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """Store a value with current timestamp."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        """Purge all cached entries."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


# ── Singleton cache instances used across services ──────────────────────
geocode_cache = TTLCache(max_size=500, ttl_seconds=86400)       # 24h
geocoding_cache = geocode_cache  # alias for backward compat
distance_matrix_cache = TTLCache(max_size=2000, ttl_seconds=86400)
directions_cache = TTLCache(max_size=500, ttl_seconds=86400)

