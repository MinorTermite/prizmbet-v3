# -*- coding: utf-8 -*-
"""
Generate frontend/matches.json from live parser data.

Runs all parsers directly (no Supabase required) and writes the JSON file
in the legacy frontend format expected by index.html:
  { last_update, source, total, matches: [{team1, team2, p1, x, p2, ...}] }
"""
import sys
import json
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Allow running as both `python backend/api/generate_json.py` and
# `python -m backend.api.generate_json` from the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн",
             "июл", "авг", "сен", "окт", "ноя", "дек"]

# Все времена матчей — по Москве (UTC+3)
MSK = timezone(timedelta(hours=3))

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "matches.json")


def _calc_double_chance(odd_a, odd_b) -> str:
    """Calculate double chance odds from two single odds.

    Uses the combined probability formula: 1 / (1/a + 1/b).
    Returns the result formatted to 2 decimal places, or "—" when either
    odd is zero/invalid or a ZeroDivisionError occurs.
    """
    try:
        a = float(odd_a) if odd_a else 0
        b = float(odd_b) if odd_b else 0
        if a > 0 and b > 0:
            result = 1.0 / (1.0/a + 1.0/b)
            if result < 1.01:
                return "—"  # not offered when implied probability > 99%
            return f"{result:.2f}"
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return "—"


def _fmt_odd(value) -> str:
    """Format an odds float to a display string."""
    try:
        v = float(value)
        return f"{v:.2f}" if v > 0 else "—"
    except (TypeError, ValueError):
        return "—"


def _bookmaker_from_id(external_id: str) -> str:
    eid = (external_id or "").lower()
    if eid.startswith("apifootball_"):
        return "ApiFootball"
    if eid.startswith("odds_") or eid.startswith("oddsio_"):
        return "OddsAPI"
    if eid.startswith("1xbet_live"):   # must come before the generic 1xbet_ check
        return "1xBet Live"
    if eid.startswith("1xbet_"):
        return "1xBet"
    if eid.startswith("leon_"):
        return "Leonbets"
    if eid.startswith("pinnacle_"):
        return "Pinnacle"
    return "unknown"


def to_frontend(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert parser match dict → legacy frontend dict."""
    date_str = time_str = ""
    raw_time = match.get("match_time", "")
    match_dt = None
    if raw_time:
        try:
            dt = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
            match_dt = dt.astimezone(MSK)
            # Filter: Skip matches more than 3 days ahead
            now = datetime.now(MSK)
            if (match_dt - now).days > 3:
                return None
            
            date_str = f"{match_dt.day} {MONTHS_RU[match_dt.month - 1]}"
            time_str = match_dt.strftime("%H:%M")
        except Exception:
            pass

    odds_1 = match.get("odds_1", 0)
    odds_x = match.get("odds_x", 0)
    odds_2 = match.get("odds_2", 0)
    
    # Filter: Skip matches with no odds at all
    if not odds_1 and not odds_x and not odds_2:
        return None

    t_val = match.get("total_value")
    t_over = match.get("total_over")
    t_under = match.get("total_under")
    
    # Принудительно устанавливаем тотал = 2.5 (если букмекер дал другую линию)
    try:
        if t_val is not None and float(t_val) != 0:
            t_val = 2.5
    except (ValueError, TypeError):
        pass
        
    out = {
        "sport":     match.get("sport", ""),
        "league":    match.get("league", ""),
        "id":        match.get("external_id", ""),
        "date":      date_str,
        "time":      time_str,
        # ISO timestamp в МСК (UTC+3)
        "match_time": match_dt.isoformat() if match_dt else "",
        "team1":     match.get("home_team", ""),
        "team2":     match.get("away_team", ""),
        "match_url": match.get("match_url", ""),
        "p1":        _fmt_odd(odds_1),
        "x":         _fmt_odd(odds_x),
        "p2":        _fmt_odd(odds_2),
        "p1x":       _calc_double_chance(odds_1, odds_x),
        "p12":       _calc_double_chance(odds_1, odds_2),
        "px2":       _calc_double_chance(odds_x, odds_2),
        "source":    _bookmaker_from_id(match.get("external_id", "")),
        "total_over":       _fmt_odd(t_over),
        "total_under":      _fmt_odd(t_under),
        "handicap_1":       _fmt_odd(match.get("handicap_1")),
        "handicap_2":       _fmt_odd(match.get("handicap_2")),
        "is_live":          bool(match.get("is_live", False)),
    }
    
    # Compact: Only include optional fields if they have value
    if t_val is not None: out["total_value"] = t_val
    if match.get("handicap_1_value") is not None: out["handicap_1_value"] = match.get("handicap_1_value")
    if match.get("handicap_2_value") is not None: out["handicap_2_value"] = match.get("handicap_2_value")
    if match.get("score"): out["score"] = match.get("score")
    
    return out


def _write_json(matches: List[Dict[str, Any]]) -> int:
    """Serialize converted matches to frontend/matches.json and return count."""
    if not matches:
        print("[generate_json] WARNING: No matches collected — keeping existing matches.json intact")
        return 0
    
    # Сохраняем результаты завершённых матчей (с полем score) из предыдущего файла на 24 часа
    out = os.path.normpath(OUT_PATH)
    scored_old = []
    try:
        if os.path.exists(out):
            with open(out, "r", encoding="utf-8") as f:
                old_payload = json.load(f)
            for m in old_payload.get("matches", []):
                if m.get("score"):
                    scored_old.append(m)
    except Exception:
        pass
    
    # Собираем ID новых матчей, чтобы не дублировать
    new_ids = {m.get("id") for m in matches}
    
    # Добавляем старые завершённые (со счетом) матчи, если их нет среди новых
    # и если они не старше 24 часов
    MONTHS_RU_PARSE = {
        "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
        "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
    }
    now = datetime.now(tz=MSK)
    carried = 0
    for old_m in scored_old:
        if old_m.get("id") in new_ids:
            # Передаём score существующему матчу
            for nm in matches:
                if nm.get("id") == old_m.get("id") and not nm.get("score"):
                    nm["score"] = old_m["score"]
            continue
        
        # Проверяем давность
        try:
            ds = (old_m.get("date") or "").strip()
            ts = (old_m.get("time") or "").strip()
            if ds:
                parts = ds.split()
                day = int(parts[0])
                month = MONTHS_RU_PARSE.get(parts[1].lower(), 0)
                if month:
                    year = now.year
                    h, mn = (int(x) for x in ts.split(":")) if ":" in ts else (0, 0)
                    match_dt = datetime(year, month, day, h, mn, tzinfo=MSK)
                    hours_ago = (now - match_dt).total_seconds() / 3600
                    if hours_ago <= 24:
                        matches.append(old_m)
                        carried += 1
                        continue
        except Exception:
            pass
    
    if carried:
        print(f"[generate_json] Carried over {carried} finished matches with scores (24h retention)")
    
    final_doc = {
        "last_update": datetime.now(tz=MSK).isoformat(timespec='seconds'),
        "source": "multi-parser",
        "total": len(matches),
        "matches": matches
    }

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(final_doc, f, ensure_ascii=False, indent=2)

    print(f"[generate_json] Wrote {len(matches)} matches -> {out}")

    # Write matches-today.json — only today + tomorrow (fast first load on frontend)
    now_msk = datetime.now(tz=MSK)
    today_day = now_msk.day
    tomorrow_day = (now_msk + timedelta(days=1)).day
    today_matches = [
        m for m in matches
        if _match_day(m) in (today_day, tomorrow_day) or m.get("score")
    ]
    today_doc = {
        "last_update": final_doc["last_update"],
        "source": "multi-parser",
        "total": len(matches),          # keep full total for stats display
        "today_total": len(today_matches),
        "matches": today_matches
    }
    today_out = out.replace("matches.json", "matches-today.json")
    with open(today_out, "w", encoding="utf-8") as f:
        json.dump(today_doc, f, ensure_ascii=False, indent=2)
    print(f"[generate_json] Wrote {len(today_matches)} today/tomorrow matches -> {today_out}")

    return len(matches)


def _match_day(match: Dict[str, Any]) -> int:
    """Extract numeric day from match 'date' field (e.g. '6 мар' → 6)."""
    try:
        return int((match.get("date") or "").split()[0])
    except (ValueError, IndexError):
        return -1


async def collect_all_matches() -> List[Dict[str, Any]]:
    """Run all parsers concurrently and return combined match list."""
    from backend.parsers.odds_api_parser import OddsAPIParser
    from backend.parsers.xbet_parser import XBetParser
    from backend.parsers.leonbets_parser import LeonbetsParser
    from backend.parsers.pinnacle_parser import PinnacleParser
    from backend.parsers.api_football_parser import ApiFootballParser
    from backend.utils.proxy_manager import proxy_manager
    from backend.config import config

    # Pre-fetch proxies if enabled
    if config.PROXY_ENABLED:
        await proxy_manager.init()
        proxy = proxy_manager.get_proxy()
        if proxy:
            print(f"[generate_json] Using proxy: {proxy}")
        elif not config.PROXY_URL:
            print("[generate_json] WARNING: Proxy enabled but no working proxies found")

    parsers = [
        OddsAPIParser(),
        XBetParser(),
        LeonbetsParser(),
        PinnacleParser(),
        ApiFootballParser(),
    ]

    results = await asyncio.gather(
        *[p.parse() for p in parsers],
        return_exceptions=True,
    )

    all_matches: List[Dict[str, Any]] = []
    names = ["OddsAPI", "1xBet", "Leonbets", "Pinnacle", "ApiFootball"]
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            print(f"[generate_json] {name} error: {result}")
        elif isinstance(result, list):
            print(f"[generate_json] {name}: {len(result)} matches")
            all_matches.extend(result)

    # Close all sessions
    for p in parsers:
        await p.close_session()

    return all_matches


async def generate_from_raw(raw: List[Dict[str, Any]]) -> int:
    """Convert pre-collected parser matches and write frontend/matches.json.

    Use this when the caller has already run the parsers (e.g. run_parsers.py)
    to avoid running the full parser network a second time.
    """
    matches = []
    for m in raw:
        fm = to_frontend(m)
        if fm:
            matches.append(fm)
    return _write_json(matches)


async def generate() -> int:
    """Run parsers, convert, write frontend/matches.json."""
    print("[generate_json] Starting parser run…")
    raw = await collect_all_matches()
    matches = []
    for m in raw:
        fm = to_frontend(m)
        if fm:
            matches.append(fm)
    return _write_json(matches)

if __name__ == "__main__":
    asyncio.run(generate())

