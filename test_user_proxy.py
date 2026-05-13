
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import sys

async def check_proxy(proxy_url):
    print(f"Checking proxy: {proxy_url}")
    connector = ProxyConnector.from_url(proxy_url)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get('https://api.ipify.org?format=json', timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"SUCCESS! Proxy is working. External IP: {data.get('ip')}")
                    return True
                else:
                    print(f"FAILED! Status code: {response.status}")
                    return False
    except Exception as e:
        print(f"FAILED! Error: {e}")
        return False

if __name__ == "__main__":
    # proxy_str = "45.81.77.14:8000:LNbHRm:tHCxnE"
    # Format: socks5://user:pass@host:port
    host = "45.81.77.14"
    port = "8000"
    user = "LNbHRm"
    password = "tHCxnE"
    
    proxy_url = f"socks5://{user}:{password}@{host}:{port}"
    asyncio.run(check_proxy(proxy_url))
