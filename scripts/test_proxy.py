# -*- coding: utf-8 -*-
"""Test proxy connection"""
import asyncio
import aiohttp

PROXY_URLS = [
    "http://LNbHRm:tHCxnE@45.81.77.14:8000",
    "https://LNbHRm:tHCxnE@45.81.77.14:8000",
    "45.81.77.14:8000:LNbHRm:tHCxnE",
]
TEST_URL = "https://google.com"

async def test_proxy():
    for proxy_url in PROXY_URLS:
        print(f"\n{'='*50}")
        print(f"Testing: {proxy_url}")
        print(f"{'='*50}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    TEST_URL,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    print(f"  OK Status: {resp.status}")
            except Exception as e:
                print(f"  XX Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy())
