# -*- coding: utf-8 -*-
import asyncio
import sys
import os
import aiohttp
from backend.utils.redis_client import cache
from backend.config import config

async def check_redis():
    print("Checking Redis connection...")
    await cache.connect()
    if cache.initialized:
        test_val = "health_check_ok"
        await cache.set("health_test", test_val, expire=10)
        val = await cache.get("health_test")
        if val == test_val:
            print("[+] Redis: OK")
            return True
    print("[-] Redis: Failed (Check URL/Token in .env)")
    return False

async def check_supabase():
    print("Checking Supabase connection...")
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.SUPABASE_URL}/rest/v1/matches?select=count"
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}"
            }
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    print("[+] Supabase: OK")
                    return True
                else:
                    print(f"[-] Supabase: Failed (Status {resp.status})")
    except Exception as e:
        print(f"[-] Supabase: Error ({e})")
    return False

async def main():
    print("--- PrizmBet v2 Health Check ---")
    r_ok = await check_redis()
    s_ok = await check_supabase()
    
    if r_ok and s_ok:
        print("\nALL SYSTEMS GO!")
    else:
        print("\nSYSTEMS NOT READY: Check .env and network.")

if __name__ == "__main__":
    asyncio.run(main())
