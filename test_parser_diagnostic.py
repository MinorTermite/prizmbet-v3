
import asyncio
import os
import sys

# Add project root to sys.path
_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.parsers.odds_api_parser import OddsAPIParser
from backend.api.generate_json import to_frontend

async def test():
    print("Testing OddsAPIParser...")
    parser = OddsAPIParser()
    await parser.init_session()
    matches = await parser.parse()
    print(f"Total matches from parser: {len(matches)}")
    if matches:
        print(f"First match raw: {matches[0]}")
        fm = to_frontend(matches[0])
        print(f"First match converted: {fm}")
    await parser.close_session()

if __name__ == "__main__":
    asyncio.run(test())
