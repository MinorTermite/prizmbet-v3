# -*- coding: utf-8 -*-
"""Test 1xBet through the SOCKS/HTTP proxy configured in PROXY_URL."""
import asyncio
import os

import aiohttp
from aiohttp_socks import ProxyConnector
from dotenv import load_dotenv

load_dotenv()

PROXY_URL = os.getenv("PROXY_URL", "").strip()
TEST_URL = os.getenv(
    "XBET_TEST_URL",
    "https://1xbet.com/LineFeed/Get1x2_VZip?sports=1&count=5&lng=ru&mode=4",
)


async def test_1xbet() -> bool:
    if not PROXY_URL:
        print("PROXY_URL is not configured")
        return False

    print("Testing 1xBet through configured proxy")
    connector = ProxyConnector.from_url(PROXY_URL)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(TEST_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                content = await response.read()
                print(f"Status: {response.status}")
                print(f"Content length: {len(content)} bytes")
                return response.status == 200
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}")
        return False
    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(test_1xbet())
