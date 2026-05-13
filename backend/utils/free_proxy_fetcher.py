# -*- coding: utf-8 -*-
"""
Free Proxy List for 1xBet and other geo-blocked APIs
Sources: public proxy lists (update regularly)
Usage: Run this script to fetch and test free proxies
"""

import asyncio
import aiohttp
from datetime import datetime

# Free proxy sources (publicly available)
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=ru&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http&country=ru",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
]

# Test URL (1xBet or similar)
TEST_URL = "https://1xbet.com"

async def test_proxy(session: aiohttp.ClientSession, proxy_url: str) -> dict:
    """Test a proxy and return result dict."""
    result = {
        "url": proxy_url,
        "working": False,
        "ms": float("inf"),
        "error": None,
    }
    
    try:
        start = datetime.now()
        async with session.get(TEST_URL, timeout=aiohttp.ClientTimeout(total=10), proxy=proxy_url) as resp:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            if resp.status == 200:
                result["working"] = True
                result["ms"] = elapsed
                print(f"✓ {proxy_url} - {elapsed:.0f}ms")
            else:
                result["error"] = f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)
    
    return result

async def fetch_proxies() -> list:
    """Fetch proxies from all sources."""
    proxies = []
    
    for source_url in PROXY_SOURCES:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        lines = text.strip().split("\n")
                        for line in lines:
                            line = line.strip()
                            if line and ":" in line and not line.startswith("#"):
                                # Convert to full URL format if needed
                                if "://" not in line:
                                    line = f"http://{line}"
                                proxies.append(line)
                        print(f"Fetched {len(lines)} proxies from {source_url[:50]}...")
        except Exception as e:
            print(f"Failed to fetch from {source_url}: {e}")
    
    return proxies

async def main():
    print("=== Free Proxy Fetcher & Tester ===")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Fetch proxies
    print("\nFetching proxies from public sources...")
    proxies = await fetch_proxies()
    print(f"Total proxies fetched: {len(proxies)}")
    
    if not proxies:
        print("No proxies found. Check proxy sources.")
        return
    
    # Test proxies
    print(f"\nTesting {len(proxies)} proxies against {TEST_URL}...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [test_proxy(session, p) for p in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter working proxies
    working = [
        r for r in results 
        if isinstance(r, dict) and r.get("working")
    ]
    working.sort(key=lambda x: x["ms"])
    
    print(f"\n=== Results ===")
    print(f"Working proxies: {len(working)}/{len(proxies)}")
    
    if working:
        print("\nTop 5 fastest proxies:")
        for i, proxy in enumerate(working[:5], 1):
            print(f"  {i}. {proxy['url']} - {proxy['ms']:.0f}ms")
        
        # Save to file
        with open("working_proxies.txt", "w", encoding="utf-8") as f:
            for proxy in working:
                f.write(f"{proxy['url']}\n")
        print(f"\nSaved {len(working)} working proxies to working_proxies.txt")
    else:
        print("\nNo working proxies found. Try again later or use paid proxies.")

if __name__ == "__main__":
    asyncio.run(main())
