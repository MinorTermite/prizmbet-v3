#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Odds API Parser -- supports two providers:

  1. the-odds-api.com  (ODDS_API_KEY)
     Events include inline bookmakers/odds -- one request per sport.

  2. odds-api.io       (ODDS_API_IO_KEY)
     Events and odds are separate endpoints.
     GET /v3/events?sport=...&status=pending  -> list of upcoming events
     GET /v3/odds?eventId=...&bookmakers=...  -> odds per event
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from backend.parsers.base_parser import BaseParser

# Provider 1: the-odds-api.com
API_KEY      = os.getenv("ODDS_API_KEY", "")
BASE_URL     = "https://api.the-odds-api.com/v4"

# Provider 2: odds-api.io
API_IO_KEY   = os.getenv("ODDS_API_IO_KEY", "")
BASE_IO_URL  = "https://api.odds-api.io/v3"
IO_BOOKMAKER = "1xbet"  # bookmaker available on free plan

# Sports to fetch from the-odds-api.com
# Free plan: 500 requests/month, 10 requests/minute
# Optimized: Only top 3 leagues to stay within limits
ODDS_API_SPORTS: Dict[str, Tuple[str, str]] = {
    "soccer_uefa_champions_league": ("football", "Liga Chempionov UEFA"),
    "soccer_epl":                   ("football", "Angliya. Premier-liga"),
    "soccer_spain_la_liga":         ("football", "Ispaniya. La Liga"),
    # Disabled to save quota:
    # "soccer_germany_bundesliga":    ("football", "Germaniya. Bundesliga"),
    # "soccer_italy_serie_a":         ("football", "Italiya. Seriya A"),
    # "basketball_nba":               ("basket",   "NBA"),
    # "icehockey_nhl":                ("hockey",   "NHL"),
}

# Top-league slug keywords for odds-api.io filtering
# Free plan: 60 requests/day, rate limited
# Optimized: Only most popular leagues
IO_TOP_SLUGS = [
    "premier-league", "la-liga", "bundesliga", "serie-a", "ligue-1",
    "champions-league", "europa-league",
    "russian-premier",  # РПЛ - приоритет для RU аудитории
    "nba", "nhl", "khl",
]

# Sports to fetch from odds-api.io
# Disabled ice-hockey to save quota (use Leonbets instead)
IO_SPORTS = ["football", "basketball"]

# Max events per sport on odds-api.io (limits per-event requests)
# Reduced from 60 to 25 to stay within rate limits
IO_MAX_EVENTS_PER_SPORT = 25


class OddsAPIParser(BaseParser):
    """The Odds API v4 + odds-api.io v3 Parser"""

    def __init__(self):
        super().__init__("OddsAPI", BASE_URL)

    async def parse(self) -> List[Dict]:
        all_matches: List[Dict] = []
        seen: set = set()

        tasks = []
        if API_KEY:
            tasks.append(self._parse_odds_api_com())
        if API_IO_KEY:
            tasks.append(self._parse_odds_api_io())

        if not tasks:
            print("[OddsAPI] No API key configured -- skipping")
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                print(f"[OddsAPI] parser error: {r}")
            elif isinstance(r, list):
                for m in r:
                    uid = m.get("external_id", "")
                    if uid and uid not in seen:
                        seen.add(uid)
                        all_matches.append(m)

        return all_matches

    # Provider 1 -- the-odds-api.com

    async def _parse_odds_api_com(self) -> List[Dict]:
        matches = []
        await self.init_session()
        for sport_key, (sport_type, league_name) in ODDS_API_SPORTS.items():
            url = f"{BASE_URL}/sports/{sport_key}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": "eu,us",
                "markets": "h2h,totals,alternate_totals,spreads",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }
            try:
                async with self.session.get(url, params=params, proxy=self.proxy) as r:
                    if r.status != 200:
                        print(f"[OddsAPI] the-odds-api.com {r.status} for {sport_key}")
                        continue
                    remaining = r.headers.get("x-requests-remaining", "?")
                    print(f"  [QUOTA] the-odds-api.com / {sport_key}: remaining={remaining}")
                    data = await r.json()
                    for event in data:
                        m = self._parse_odds_api_com_event(event, sport_type, league_name)
                        if m:
                            matches.append(m)
            except Exception as e:
                print(f"[OddsAPI] the-odds-api.com error {sport_key}: {e}")
        return matches

    def _parse_odds_api_com_event(self, event: Dict, sport_type: str, league_name: str) -> Optional[Dict]:
        event_id  = event.get("id", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence  = event.get("commence_time", "")
        try:
            match_time = datetime.fromisoformat(commence.replace("Z", "+00:00")).isoformat()
        except Exception:
            match_time = commence

        md: Dict = {
            "external_id":       f"odds_{event_id}",
            "sport":             sport_type,
            "league":            league_name,
            "home_team":         home_team,
            "away_team":         away_team,
            "match_time":        match_time,
            "is_live":           False,
            "odds_1":            0.0,
            "odds_x":            0.0,
            "odds_2":            0.0,
            "total_value":       None,
            "total_over":        0.0,
            "total_under":       0.0,
            "handicap_1_value":  None,
            "handicap_1":        0.0,
            "handicap_2_value":  None,
            "handicap_2":        0.0,
        }

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return None
        bk = bookmakers[0]
        for market in bk.get("markets", []):
            key      = market.get("key", "")
            outcomes = market.get("outcomes", [])
            if key == "h2h":
                for o in outcomes:
                    n = o.get("name", "")
                    p = float(o.get("price", 0) or 0)
                    if n == home_team:   md["odds_1"] = p
                    elif n == away_team: md["odds_2"] = p
                    elif n == "Draw":    md["odds_x"] = p
                if sport_type in ("tennis", "basket"):
                    md["odds_x"] = 0.0
            elif key in ("totals", "alternate_totals"):
                # Ищем конкретно линию 2.5
                best_over = None
                best_under = None
                best_point = None
                fallback_over = None
                fallback_under = None
                fallback_point = None
                for o in outcomes:
                    n = o.get("name", "")
                    p = float(o.get("price", 0) or 0)
                    pt = o.get("point", 0)
                    pt_val = float(pt) if pt else None
                    if pt_val == 2.5:
                        if n == "Over":
                            best_over = p
                            best_point = pt_val
                        elif n == "Under":
                            best_under = p
                    elif fallback_point is None and n == "Over":
                        fallback_over = p
                        fallback_point = pt_val
                    elif fallback_point is not None and n == "Under" and fallback_under is None:
                        fallback_under = p
                
                # Предпочитаем 2.5, иначе берём основную линию
                if best_point is not None:
                    md["total_value"] = best_point
                    md["total_over"] = best_over or 0.0
                    md["total_under"] = best_under or 0.0
                elif fallback_point is not None and md["total_value"] is None:
                    md["total_value"] = fallback_point
                    md["total_over"] = fallback_over or 0.0
                    md["total_under"] = fallback_under or 0.0
            elif key == "spreads":
                for o in outcomes:
                    n  = o.get("name", "")
                    p  = float(o.get("price", 0) or 0)
                    pt = float(o.get("point", 0) or 0)
                    if n == home_team:
                        md["handicap_1_value"] = pt
                        md["handicap_1"]       = p
                    elif n == away_team:
                        md["handicap_2_value"] = pt
                        md["handicap_2"]       = p

        if not md["odds_1"] and not md["odds_2"]:
            return None
        return md

    # Provider 2 -- odds-api.io

    async def _parse_odds_api_io(self) -> List[Dict]:
        await self.init_session()
        all_matches: List[Dict] = []

        for sport in IO_SPORTS:
            try:
                events = await self._io_get_events(sport)
            except Exception as e:
                print(f"[OddsAPI.io] events error ({sport}): {e}")
                continue

            # Filter to top leagues and limit count
            filtered = [
                e for e in events
                if isinstance(e.get("league"), dict)
                and any(slug in e["league"].get("slug", "") for slug in IO_TOP_SLUGS)
            ]
            filtered.sort(key=lambda e: e.get("date", ""))
            filtered = filtered[:IO_MAX_EVENTS_PER_SPORT]

            print(f"[OddsAPI.io] {sport}: {len(events)} total events, {len(filtered)} top-league selected")

            # Fetch odds concurrently
            odds_tasks = [self._io_get_odds(e["id"]) for e in filtered]
            odds_results = await asyncio.gather(*odds_tasks, return_exceptions=True)

            for event, odds_data in zip(filtered, odds_results):
                if isinstance(odds_data, Exception) or not odds_data:
                    continue
                m = self._parse_io_event(event, odds_data, sport)
                if m:
                    all_matches.append(m)

        print(f"[OddsAPI.io] Total matches collected: {len(all_matches)}")
        return all_matches

    async def _io_get_events(self, sport: str) -> List[Dict]:
        url = f"{BASE_IO_URL}/events"
        params = {"apiKey": API_IO_KEY, "sport": sport, "status": "pending"}
        async with self.session.get(url, params=params, proxy=self.proxy) as r:
            if r.status != 200:
                print(f"[OddsAPI.io] events {r.status} for sport={sport}")
                return []
            return await r.json()

    async def _io_get_odds(self, event_id: int) -> Optional[Dict]:
        url = f"{BASE_IO_URL}/odds"
        params = {"apiKey": API_IO_KEY, "eventId": event_id, "bookmakers": IO_BOOKMAKER}
        try:
            async with self.session.get(url, params=params, proxy=self.proxy) as r:
                if r.status != 200:
                    return None
                return await r.json()
        except Exception:
            return None

    def _parse_io_event(self, event: Dict, odds_resp: Dict, sport: str) -> Optional[Dict]:
        home_team = event.get("home", "")
        away_team = event.get("away", "")
        league    = event.get("league", {}) or {}
        event_id  = event.get("id", "")

        sport_map = {"football": "football", "basketball": "basket", "ice-hockey": "hockey"}
        sport_type  = sport_map.get(sport, sport)
        league_name = league.get("name", league.get("slug", ""))

        date_str = event.get("date", "")
        try:
            match_time = datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            match_time = date_str

        md: Dict = {
            "external_id":       f"oddsio_{event_id}",
            "sport":             sport_type,
            "league":            league_name,
            "home_team":         home_team,
            "away_team":         away_team,
            "match_time":        match_time,
            "is_live":           event.get("status") == "live",
            "odds_1":            0.0,
            "odds_x":            0.0,
            "odds_2":            0.0,
            "total_value":       None,
            "total_over":        0.0,
            "total_under":       0.0,
            "handicap_1_value":  None,
            "handicap_1":        0.0,
            "handicap_2_value":  None,
            "handicap_2":        0.0,
        }

        bookmakers = odds_resp.get("bookmakers", {})
        for bk_name, markets in bookmakers.items():
            if not isinstance(markets, list):
                continue
            for market in markets:
                mname  = market.get("name", "")
                odds_l = market.get("odds", [])
                if not odds_l:
                    continue
                o = odds_l[0]

                if mname == "ML":  # Match Line = 1X2
                    md["odds_1"] = float(o.get("home", 0) or 0)
                    md["odds_x"] = float(o.get("draw", 0) or 0)
                    md["odds_2"] = float(o.get("away", 0) or 0)
                    if sport_type in ("tennis", "basket"):
                        md["odds_x"] = 0.0

                elif mname in ("Total", "Over/Under", "O/U"):
                    try:
                        md["total_value"] = float(o.get("total", o.get("line", 0)) or 0) or None
                        md["total_over"]  = float(o.get("over",  o.get("home", 0)) or 0)
                        md["total_under"] = float(o.get("under", o.get("away", 0)) or 0)
                    except (TypeError, ValueError):
                        pass

                elif mname == "Spread":
                    try:
                        md["handicap_1_value"] = float(o.get("hdp", 0) or 0)
                        md["handicap_1"]       = float(o.get("home", 0) or 0)
                        md["handicap_2_value"] = -float(o.get("hdp", 0) or 0)
                        md["handicap_2"]       = float(o.get("away", 0) or 0)
                    except (TypeError, ValueError):
                        pass

            break  # use first bookmaker only

        if not md["odds_1"] and not md["odds_2"]:
            return None
        return md
