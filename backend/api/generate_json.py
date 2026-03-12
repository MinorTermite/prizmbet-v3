# -*- coding: utf-8 -*-
"""
Generate frontend/matches.json from parser data without requiring Supabase.

Primary source: Leonbets public line.
Optional enrichers: OddsAPI, ApiFootball, Pinnacle, 1xBet.

Only totals with a line value <= 2.5 are allowed into the frontend payload.
If a source provides only higher totals, the total market is omitted entirely.
"""

import sys
import json
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Iterable


_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
MONTHS_RU_PARSE = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}
MSK = timezone(timedelta(hours=3))
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "matches.json")
ENABLE_XBET = os.getenv("ENABLE_XBET", "false").strip().lower() == "true"


def _calc_double_chance(odd_a: Any, odd_b: Any) -> str:
    try:
        a = float(odd_a) if odd_a else 0
        b = float(odd_b) if odd_b else 0
        if a > 0 and b > 0:
            result = 1.0 / (1.0 / a + 1.0 / b)
            return f"{result:.2f}" if result >= 1.01 else "—"
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return "—"


def _fmt_odd(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:.2f}" if number > 0 else "—"


def _bookmaker_from_id(external_id: str) -> str:
    eid = (external_id or "").lower()
    if eid.startswith("apifootball_"):
        return "ApiFootball"
    if eid.startswith("odds_") or eid.startswith("oddsio_"):
        return "OddsAPI"
    if eid.startswith("1xbet_live"):
        return "1xBet Live"
    if eid.startswith("1xbet_"):
        return "1xBet"
    if eid.startswith("leon_"):
        return "Leonbets"
    if eid.startswith("pinnacle_"):
        return "Pinnacle"
    return "unknown"


def _sanitize_total_line(match: Dict[str, Any]) -> tuple[Optional[float], Any, Any]:
    raw_total = match.get("total_value")
    raw_over = match.get("total_over")
    raw_under = match.get("total_under")

    try:
        total_value = float(raw_total)
    except (TypeError, ValueError):
        return None, None, None

    if total_value <= 0 or total_value > 2.5:
        return None, None, None

    try:
        over_value = float(raw_over) if raw_over not in (None, "", "—") else None
    except (TypeError, ValueError):
        over_value = None
    try:
        under_value = float(raw_under) if raw_under not in (None, "", "—") else None
    except (TypeError, ValueError):
        under_value = None

    return round(total_value, 1), over_value, under_value


def to_frontend(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    date_str = ""
    time_str = ""
    match_dt = None
    raw_time = match.get("match_time", "")

    if raw_time:
        try:
            dt = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
            match_dt = dt.astimezone(MSK)
            if (match_dt - datetime.now(MSK)).days > 3:
                return None
            date_str = f"{match_dt.day} {MONTHS_RU[match_dt.month - 1]}"
            time_str = match_dt.strftime("%H:%M")
        except Exception:
            pass

    odds_1 = match.get("odds_1", 0)
    odds_x = match.get("odds_x", 0)
    odds_2 = match.get("odds_2", 0)
    if not odds_1 and not odds_x and not odds_2:
        return None

    total_value, total_over, total_under = _sanitize_total_line(match)

    out = {
        "sport": match.get("sport", ""),
        "league": match.get("league", ""),
        "id": match.get("external_id", ""),
        "date": date_str,
        "time": time_str,
        "match_time": match_dt.isoformat() if match_dt else "",
        "team1": match.get("home_team", ""),
        "team2": match.get("away_team", ""),
        "match_url": match.get("match_url", ""),
        "p1": _fmt_odd(odds_1),
        "x": _fmt_odd(odds_x),
        "p2": _fmt_odd(odds_2),
        "p1x": _calc_double_chance(odds_1, odds_x),
        "p12": _calc_double_chance(odds_1, odds_2),
        "px2": _calc_double_chance(odds_x, odds_2),
        "source": _bookmaker_from_id(match.get("external_id", "")),
        "total_over": _fmt_odd(total_over),
        "total_under": _fmt_odd(total_under),
        "handicap_1": _fmt_odd(match.get("handicap_1")),
        "handicap_2": _fmt_odd(match.get("handicap_2")),
        "is_live": bool(match.get("is_live", False)),
    }

    if total_value is not None:
        out["total_value"] = total_value
    if match.get("handicap_1_value") is not None:
        out["handicap_1_value"] = match.get("handicap_1_value")
    if match.get("handicap_2_value") is not None:
        out["handicap_2_value"] = match.get("handicap_2_value")
    if match.get("score"):
        out["score"] = match.get("score")

    return out


def _match_day(match: Dict[str, Any]) -> int:
    try:
        return int((match.get("date") or "").split()[0])
    except (ValueError, IndexError):
        return -1


def _iter_finished_from_previous(path: str) -> Iterable[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return []
    return [item for item in payload.get("matches", []) if item.get("score")]


def _write_json(matches: List[Dict[str, Any]]) -> int:
    if not matches:
        print("[generate_json] WARNING: no matches collected; keeping current payload intact")
        return 0

    out = os.path.normpath(OUT_PATH)
    scored_old = list(_iter_finished_from_previous(out))
    new_ids = {item.get("id") for item in matches}
    now = datetime.now(MSK)
    carried = 0

    for old_match in scored_old:
        old_id = old_match.get("id")
        if old_id in new_ids:
            for current in matches:
                if current.get("id") == old_id and not current.get("score"):
                    current["score"] = old_match["score"]
            continue

        try:
            date_bits = str(old_match.get("date") or "").split()
            time_text = str(old_match.get("time") or "").strip()
            if len(date_bits) >= 2:
                day = int(date_bits[0])
                month = MONTHS_RU_PARSE.get(date_bits[1].lower())
                if month:
                    hour, minute = (int(part) for part in time_text.split(":")) if ":" in time_text else (0, 0)
                    match_dt = datetime(now.year, month, day, hour, minute, tzinfo=MSK)
                    hours_ago = (now - match_dt).total_seconds() / 3600
                    if 0 <= hours_ago <= 24:
                        matches.append(old_match)
                        carried += 1
        except Exception:
            continue

    if carried:
        print(f"[generate_json] carried over {carried} finished matches for 24h retention")

    matches.sort(key=lambda item: (
        0 if item.get("is_live") else 1,
        item.get("match_time") or "9999-12-31T00:00:00+03:00",
        item.get("league") or "",
        item.get("team1") or "",
    ))

    final_doc = {
        "last_update": datetime.now(MSK).isoformat(timespec="seconds"),
        "source": "multi-parser",
        "total": len(matches),
        "matches": matches,
    }

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(final_doc, fh, ensure_ascii=False, indent=2)
    print(f"[generate_json] wrote {len(matches)} matches -> {out}")

    now_msk = datetime.now(MSK)
    today_day = now_msk.day
    tomorrow_day = (now_msk + timedelta(days=1)).day
    today_matches = [
        item for item in matches
        if _match_day(item) in (today_day, tomorrow_day) or item.get("score")
    ]
    today_doc = {
        "last_update": final_doc["last_update"],
        "source": "multi-parser",
        "total": len(matches),
        "today_total": len(today_matches),
        "matches": today_matches,
    }
    today_out = out.replace("matches.json", "matches-today.json")
    with open(today_out, "w", encoding="utf-8") as fh:
        json.dump(today_doc, fh, ensure_ascii=False, indent=2)
    print(f"[generate_json] wrote {len(today_matches)} today/tomorrow matches -> {today_out}")

    return len(matches)


async def collect_all_matches() -> List[Dict[str, Any]]:
    from backend.config import config
    from backend.parsers.api_football_parser import ApiFootballParser
    from backend.parsers.leonbets_parser import LeonbetsParser
    from backend.parsers.odds_api_parser import OddsAPIParser
    from backend.parsers.pinnacle_parser import PinnacleParser
    from backend.parsers.xbet_parser import XBetParser
    from backend.utils.proxy_manager import proxy_manager

    if config.PROXY_ENABLED:
        await proxy_manager.init()
        proxy = proxy_manager.get_proxy()
        if proxy:
            print(f"[generate_json] using proxy: {proxy}")
        elif not config.PROXY_URL:
            print("[generate_json] WARNING: proxy enabled but no working proxies found")

    parser_specs = [
        ("Leonbets", LeonbetsParser, True),
        ("OddsAPI", OddsAPIParser, bool(config.ODDS_API_KEY or config.ODDS_API_IO_KEY)),
        ("ApiFootball", ApiFootballParser, bool(config.API_FOOTBALL_KEY)),
        ("Pinnacle", PinnacleParser, bool(config.PINNACLE_LOGIN and config.PINNACLE_PASSWORD)),
        ("1xBet", XBetParser, ENABLE_XBET),
    ]

    all_matches: List[Dict[str, Any]] = []
    for name, parser_cls, enabled in parser_specs:
        if not enabled:
            print(f"[generate_json] {name}: skipped")
            continue

        parser = parser_cls()
        try:
            result = await parser.parse()
            if isinstance(result, list):
                print(f"[generate_json] {name}: {len(result)} matches")
                all_matches.extend(result)
        except Exception as exc:
            print(f"[generate_json] {name} error: {exc}")
        finally:
            await parser.close_session()

    return all_matches


async def generate_from_raw(raw: List[Dict[str, Any]]) -> int:
    matches = []
    for item in raw:
        converted = to_frontend(item)
        if converted:
            matches.append(converted)
    return _write_json(matches)


async def generate() -> int:
    print("[generate_json] Starting parser run...")
    raw = await collect_all_matches()
    return await generate_from_raw(raw)


if __name__ == "__main__":
    asyncio.run(generate())
