# -*- coding: utf-8 -*-
"""Main Parser Runner"""
import asyncio
import sys
import os

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.db.supabase_client import db
from backend.utils.redis_client import cache

async def run_all_parsers():
    """Run all parsers, save to Supabase/cache, and write frontend/matches.json."""
    print("=" * 50)
    print("PrizmBet v2 - Parser Runner")
    print("=" * 50)

    db.init()
    await cache.connect()

    try:
        from backend.parsers.odds_api_parser import OddsAPIParser
        from backend.parsers.xbet_parser import XBetParser
        from backend.parsers.leonbets_parser import LeonbetsParser
        from backend.parsers.pinnacle_parser import PinnacleParser
        from backend.parsers.api_football_parser import ApiFootballParser

        parsers = [
            OddsAPIParser(),
            XBetParser(),
            LeonbetsParser(),
            PinnacleParser(),
            ApiFootballParser(),
        ]

        tasks = [parser.run() for parser in parsers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_matches = sum(r for r in results if isinstance(r, int))
        print(f"\nTotal matches parsed: {total_matches}")

        # Collect already-parsed matches from all parsers (avoids re-running the API calls).
        # BaseParser.__init__ always sets self.matches = [], so getattr is a safe fallback.
        all_matches = [m for parser in parsers for m in getattr(parser, "matches", [])]
        if all_matches:
            try:
                from backend.api.generate_json import generate_from_raw
                await generate_from_raw(all_matches)
            except Exception as e:
                print(f"[run_parsers] generate_json failed: {type(e).__name__}: {e}")
    finally:
        await cache.close()

    # Обогащаем matches.json финальными счетами завершённых матчей
    try:
        from backend.score_enricher import main as enrich_scores
        await enrich_scores()
    except Exception as e:
        print(f"[run_parsers] score_enricher failed: {type(e).__name__}: {e}")

    try:
        from backend.bot.v3_settler import run_once as settle_v3_bets_once
        settled = await settle_v3_bets_once()
        print(f"[run_parsers] v3_settler settled {settled} bet(s)")
    except Exception as e:
        print(f"[run_parsers] v3_settler failed: {type(e).__name__}: {e}")

PARSER_INTERVAL_SECONDS = int(os.getenv("PARSER_INTERVAL_SECONDS", "300"))


async def run_parsers_loop():
    """Run parsers in a loop every PARSER_INTERVAL_SECONDS (default 5 min)."""
    while True:
        try:
            await run_all_parsers()
        except Exception as e:
            print(f"[run_parsers] loop error: {type(e).__name__}: {e}")
        await asyncio.sleep(PARSER_INTERVAL_SECONDS)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        asyncio.run(run_parsers_loop())
    else:
        asyncio.run(run_all_parsers())
