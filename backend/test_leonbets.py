import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.parsers.leonbets_parser import LeonbetsParser

async def test():
    p = LeonbetsParser()
    await p.init_session()
    
    # Custom fetch to get raw data
    url = f"{p.base_url}/api-2/betline/events/all"
    params = {"ctag": "ru-RU", "flags": "all"}
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://leon.ru/",
    }
    
    families = set()
    async with p.session.get(url, params=params, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            events = data.get("events", [])
            for e in events:
                league_obj = e.get("league", {}) or {}
                sport_obj = league_obj.get("sport", {}) or {}
                fam = sport_obj.get("family", "")
                if fam:
                    families.add(fam)
                    
    print("Found sport families:")
    for f in sorted(list(families)):
        print("-", f)

if __name__ == "__main__":
    asyncio.run(test())
