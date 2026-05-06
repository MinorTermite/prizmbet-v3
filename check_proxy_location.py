# -*- coding: utf-8 -*-
"""Check configured proxy IP location without hardcoding credentials."""
import asyncio
import os

import aiohttp
from aiohttp_socks import ProxyConnector
from dotenv import load_dotenv

load_dotenv()

PROXY_URL = os.getenv("PROXY_URL", "").strip()


async def check_ip_location() -> bool:
    if not PROXY_URL:
        print("PROXY_URL is not configured")
        return False

    connector = ProxyConnector.from_url(PROXY_URL)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://api.ipify.org?format=json", timeout=10) as resp:
                ip_data = await resp.json()
                print(f"Proxy IP: {ip_data.get('ip', 'unknown')}")

            async with session.get("https://ipapi.co/json/", timeout=10) as resp:
                if resp.status != 200:
                    print(f"Could not get country info (status {resp.status})")
                    return False
                data = await resp.json()
                print(f"Country: {data.get('country_name', 'Unknown')}")
                print(f"City: {data.get('city', 'Unknown')}")
                print(f"ISP: {data.get('org', 'Unknown')}")
                return True
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}")
        return False
    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(check_ip_location())
