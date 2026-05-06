# -*- coding: utf-8 -*-
"""Main Parser Runner with quota-aware provider scheduling."""
import asyncio
import json
import sys
import os
import time
from collections import Counter
from pathlib import Path

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.db.supabase_client import db
from backend.utils.redis_client import cache

PARSER_STATE_FILE = Path(os.getenv(
    "PARSER_STATE_FILE",
    os.path.join(_repo_root, "backend", ".parser_schedule_state.json"),
))

PARSER_PROVIDER_INTERVALS = {
    # Public/free source. Safe to refresh often for live line freshness.
    "Leonbets": int(os.getenv("LEONBETS_INTERVAL_SECONDS", "300")),
    # Free quota: 500 requests/month. Current parser uses 6 requests/run.
    # 2 runs/day = 12 requests/day ~= 360/month, leaving reserve.
    "OddsAPI": int(os.getenv("ODDS_API_INTERVAL_SECONDS", "43200")),
    # Free quota: 100 requests/day. Parser uses date/live fixture calls plus
    # one odds call per selected fixture, so keep it conservative.
    "ApiFootball": int(os.getenv("API_FOOTBALL_INTERVAL_SECONDS", "43200")),
    # 1xBet requires a working proxy; keep independent from Leonbets.
    "1xBet": int(os.getenv("XBET_INTERVAL_SECONDS", "1800")),
    # Pinnacle is credentials-based; slower cadence is enough for backup.
    "Pinnacle": int(os.getenv("PINNACLE_INTERVAL_SECONDS", "3600")),
}

PARSER_FORCE_ALL_ON_START = os.getenv("PARSER_FORCE_ALL_ON_START", "false").lower() == "true"


def _load_schedule_state() -> dict:
    try:
        return json.loads(PARSER_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_schedule_state(state: dict) -> None:
    try:
        PARSER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PARSER_STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[run_parsers] schedule state save failed: {type(e).__name__}: {e}")


def _select_due_parsers(parsers: list, state: dict, now_ts: float) -> list:
    due = []
    for parser in parsers:
        name = getattr(parser, "name", parser.__class__.__name__)
        interval = PARSER_PROVIDER_INTERVALS.get(name, PARSER_INTERVAL_SECONDS)
        last_run = float(state.get(name, {}).get("last_run", 0) or 0)
        elapsed = now_ts - last_run
        if PARSER_FORCE_ALL_ON_START or last_run <= 0 or elapsed >= interval:
            due.append(parser)
        else:
            remaining = int(interval - elapsed)
            print(f"[run_parsers] parser={name} status=skipped next_due_in={remaining}s interval={interval}s")
    return due

async def run_all_parsers(force_all: bool = False):
    """Run all parsers, save to Supabase/cache, and write frontend/matches.json."""
    print("=" * 50)
    print("1PrizmBet v3 - Parser Runner")
    print("=" * 50)

    db.init()
    await cache.connect()

    try:
        from backend.parsers.odds_api_parser import OddsAPIParser
        from backend.parsers.xbet_parser import XBetParser
        from backend.parsers.leonbets_parser import LeonbetsParser
        from backend.parsers.pinnacle_parser import PinnacleParser
        from backend.parsers.api_football_parser import ApiFootballParser

        all_parsers = [
            OddsAPIParser(),
            XBetParser(),
            LeonbetsParser(),
            PinnacleParser(),
            ApiFootballParser(),
        ]

        state = _load_schedule_state()
        now_ts = time.time()
        parsers = all_parsers if force_all else _select_due_parsers(all_parsers, state, now_ts)

        if not parsers:
            print("[run_parsers] no parsers due in this cycle")
            return 0

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
                state[parser_name] = {
                    "last_run": now_ts,
                    "last_run_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts)),
                    "interval_seconds": PARSER_PROVIDER_INTERVALS.get(parser_name, PARSER_INTERVAL_SECONDS),
                    "buffered_count": parsed_count,
                    "result_count": result,
                }

        _save_schedule_state(state)

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
        else:
            print("[run_parsers] no fresh matches collected; keeping existing frontend JSON")
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
        asyncio.run(run_all_parsers(force_all="--force-all" in sys.argv))
