# -*- coding: utf-8 -*-
"""Auto-rotating proxy manager — fetches and tests free proxies at runtime."""

import asyncio
import json
from typing import List, Optional
from backend.utils.redis_client import cache

REDIS_KEY = "working_proxies"

class ProxyManager:
    """Reads working proxies from Redis (populated by proxy_checker.py)."""

    def __init__(self):
        self._proxies: List[dict] = []  # list of {"url": str, "ms": float}
        self._failed: set = set()

    async def init(self) -> None:
        """Fetch working proxies from Redis."""
        await self.refresh_if_needed()

    def get_proxy(self) -> Optional[str]:
        """Return the best (fastest) working proxy URL from cache."""
        for entry in self._proxies:
            url = entry["url"]
            if url not in self._failed:
                return url
        return None

    async def mark_failed(self, proxy_url: str) -> None:
        """Mark a proxy as failed so it won't be returned by THIS instance."""
        self._failed.add(proxy_url)

    async def refresh_if_needed(self) -> None:
        """Reload proxies from Redis if current list is empty or exhausted."""
        needs_refresh = not self._proxies or all(e["url"] in self._failed for e in self._proxies)
        
        if needs_refresh:
            data = await cache.get(REDIS_KEY)
            if data:
                try:
                    self._proxies = json.loads(data)
                    self._failed = set()
                    if self._proxies:
                        print(f"[ProxyManager] Loaded {len(self._proxies)} proxies from Redis.")
                except Exception as e:
                    print(f"[ProxyManager] Failed to parse Redis proxy data: {e}")
            else:
                # Fallback: silently fail, parsers will run without proxy
                self._proxies = []

proxy_manager = ProxyManager()
