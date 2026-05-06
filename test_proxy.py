# -*- coding: utf-8 -*-
"""Test proxy connection using PROXY_URL from the local environment."""
import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

PROXY_URL = os.getenv("PROXY_URL", "").strip()
TEST_URL = os.getenv("PROXY_TEST_URL", "https://google.com").strip()


async def test_proxy() -> bool:
    if not PROXY_URL:
        print("PROXY_URL is not configured")
        return False

    print("Testing configured proxy")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                TEST_URL,
                proxy=PROXY_URL,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                print(f"Status: {resp.status}")
                return resp.status < 500
        except Exception as exc:
            print(f"Error: {type(exc).__name__}: {exc}")
            return False


if __name__ == "__main__":
    asyncio.run(test_proxy())
