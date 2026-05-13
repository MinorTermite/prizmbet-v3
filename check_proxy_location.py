# -*- coding: utf-8 -*-
"""
Информация о прокси PROXY6.net

Данные:
- IP: 45.81.77.14:8000
- Login: LNbHRm
- Password: tHCxnE
- Тип: SOCKS5
- Действует до: 04.04.26 (29 дней)

Проблема:
- 1xBet требует РОССИЙСКИЙ IP
- IP 45.81.77.14 может быть в другой стране

Решение:
1. Проверить страну IP
2. Если не Россия — купить прокси с Russian IP
3. На PROXY6.net выбрать страну "Russia" при покупке
"""

import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector

PROXY_URL = "socks5://LNbHRm:tHCxnE@45.81.77.14:8000"

async def check_ip_location():
    """Проверяет страну IP адреса прокси"""
    print("Checking proxy IP location...")
    
    connector = ProxyConnector.from_url(PROXY_URL)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            # Check IP
            async with session.get('https://api.ipify.org?format=json', timeout=10) as resp:
                data = await resp.json()
                print(f"[OK] Proxy IP: {data.get('ip')}")
            
            # Check country via ipapi.co
            async with session.get('https://ipapi.co/json/', timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"[OK] Country: {data.get('country_name', 'Unknown')}")
                    print(f"[OK] City: {data.get('city', 'Unknown')}")
                    print(f"[OK] ISP: {data.get('org', 'Unknown')}")
                    
                    if data.get('country_name') != 'Russia':
                        print("\n[ERROR] Proxy is NOT in Russia!")
                        print("1xBet requires Russian IP")
                        print("\nSolution:")
                        print("1. Go to https://proxy6.net/")
                        print("2. When buying, select country 'Russia'")
                        print("3. Or use HTTP proxy with Russian IP")
                    else:
                        print("\n[OK] Proxy is in Russia - should work with 1xBet")
                else:
                    print(f"Could not get country info (status {resp.status})")
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await connector.close()

if __name__ == "__main__":
    asyncio.run(check_ip_location())
