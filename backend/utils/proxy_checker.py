# -*- coding: utf-8 -*-
"""Proxy Checker - Background process to maintain a list of working proxies in Redis."""

import asyncio
import time
import json
from typing import List
import aiohttp
from backend.utils.redis_client import cache
from backend.config import config

# Sources of free proxies
PROXY_SOURCES = [
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
    "https://vakhov.github.io/fresh-proxy-list/http.txt",
    "https://vakhov.github.io/fresh-proxy-list/socks5.txt",
]

TEST_URL = "http://httpbin.org/ip"
TEST_TIMEOUT = 5
MAX_CONCURRENT_TESTS = 30
REDIS_KEY = "working_proxies"

async def fetch_proxy_list(session: aiohttp.ClientSession, url: str) -> List[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                text = await resp.text()
                return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        pass
    return []

async def test_proxy(session: aiohttp.ClientSession, proxy_url: str) -> dict:
    start = time.monotonic()
    try:
        # Normalize URL
        full_url = proxy_url if "://" in proxy_url else f"http://{proxy_url}"
        async with session.get(
            TEST_URL,
            proxy=full_url,
            timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                ms = (time.monotonic() - start) * 1000
                return {"url": full_url, "ms": ms}
    except Exception:
        pass
    return None

async def run_check():
    print("[ProxyChecker] Starting proxy check cycle...")
    await cache.connect()
    
    async with aiohttp.ClientSession() as session:
        lists = await asyncio.gather(*[fetch_proxy_list(session, src) for src in PROXY_SOURCES])
        raw_proxies = list(set([p for lst in lists for p in lst]))
        
        print(f"[ProxyChecker] Found {len(raw_proxies)} candidates. Testing top 100...")
        candidates = raw_proxies[:100]
        
        results = []
        # Test in batches
        for i in range(0, len(candidates), MAX_CONCURRENT_TESTS):
            batch = candidates[i:i + MAX_CONCURRENT_TESTS]
            batch_results = await asyncio.gather(*[test_proxy(session, p) for p in batch])
            results.extend([r for r in batch_results if r])
        
        # Sort by speed
        results.sort(key=lambda x: x["ms"])
        
        if results:
            print(f"[ProxyChecker] Saving {len(results)} working proxies to Redis.")
            await cache.set(REDIS_KEY, json.dumps(results), expire=1800) # 30 min TTL
        else:
            print("[ProxyChecker] No working proxies found.")

if __name__ == "__main__":
    asyncio.run(run_check())
