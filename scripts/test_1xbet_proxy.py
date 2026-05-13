# -*- coding: utf-8 -*-
"""Test 1xBet via SOCKS5 proxy"""
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector

PROXY_URL = "socks5://LNbHRm:tHCxnE@45.81.77.14:8000"
TEST_URL = "https://1xbet.com/LineFeed/Get1x2_VZip?sports=1&count=5&lng=ru&mode=4"

async def test_1xbet():
    print(f"Testing 1xBet via proxy: {PROXY_URL}")
    
    connector = ProxyConnector.from_url(PROXY_URL)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(TEST_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"Status: {response.status}")
                content = await response.read()
                print(f"Content length: {len(content)} bytes")
                
                if response.status == 200:
                    print("SUCCESS! 1xBet is accessible via proxy")
                    # Try to decompress if gzip
                    if content[:2] == b'\x1f\x8b':
                        import gzip
                        content = gzip.decompress(content)
                        print(f"Decompressed: {content[:200]}")
                    else:
                        print(f"Content: {content[:200]}")
                    return True
                else:
                    print(f"FAILED! Status code: {response.status}")
                    return False
    except Exception as e:
        print(f"FAILED! Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_1xbet())
