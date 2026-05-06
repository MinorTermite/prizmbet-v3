# -*- coding: utf-8 -*-
"""Check a user-provided proxy URL without hardcoded credentials."""
import asyncio
import os
import sys

import aiohttp
from aiohttp_socks import ProxyConnector
from dotenv import load_dotenv

load_dotenv()


async def check_proxy(proxy_url: str) -> bool:
    if not proxy_url:
        print("Proxy URL is required. Pass it as argv[1] or set PROXY_URL in .env")
        return False

    print("Checking configured proxy")
    connector = ProxyConnector.from_url(proxy_url)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://api.ipify.org?format=json", timeout=15) as response:
                if response.status != 200:
                    print(f"FAILED! Status code: {response.status}")
                    return False
                data = await response.json()
                print(f"SUCCESS! Proxy is working. External IP: {data.get('ip')}")
                return True
    except Exception as exc:
        print(f"FAILED! Error: {type(exc).__name__}: {exc}")
        return False
    finally:
        await connector.close()


if __name__ == "__main__":
    proxy = sys.argv[1].strip() if len(sys.argv) > 1 else os.getenv("PROXY_URL", "").strip()
    asyncio.run(check_proxy(proxy))
