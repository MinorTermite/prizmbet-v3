# -*- coding: utf-8 -*-
"""Main Parser Runner"""
import asyncio
import sys
import os
from collections import Counter

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

        for parser, result in zip(parsers, results):
            parser_name = getattr(parser, "name", parser.__class__.__name__)
            parsed_count = len(getattr(parser, "matches", []) or [])
            if isinstance(result, Exception):
                print(f"[run_parsers] parser={parser_name} status=error parsed_count={parsed_count} error={type(result).__name__}: {result}")
            else:
                print(f"[run_parsers] parser={parser_name} status=ok result_count={result} buffered_count={parsed_count}")

        # Collect already-parsed matches from all parsers (avoids re-running the API calls).
        # BaseParser.__init__ always sets self.matches = [], so getattr is a safe fallback.
        all_matches = [m for parser in parsers for m in getattr(parser, "matches", [])]
        if all_matches:
            source_counter = Counter()
            sport_counter = Counter()
            for match in all_matches:
                source = str(match.get("external_id") or match.get("id") or "unknown").split("_", 1)[0]
                sport = str(match.get("sport") or "unknown").strip().lower()
                source_counter[source] += 1
                sport_counter[sport] += 1
            print(f"[run_parsers] collected_raw_matches={len(all_matches)} by_source={dict(source_counter)} by_sport={dict(sport_counter)}")
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
