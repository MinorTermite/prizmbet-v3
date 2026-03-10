# -*- coding: utf-8 -*-
"""
API-Football Parser (api-football.com via RapidAPI)
Docs: https://www.api-football.com/documentation-v3
Provides: fixtures, live scores, odds (pre-match and live).
"""

import os
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from backend.parsers.base_parser import BaseParser

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"

# League IDs → (sport_type, league_name)
# Optimized: Only top leagues to minimize API calls
LEAGUES: Dict[int, tuple] = {
    2:   ("football", "Лига чемпионов УЕФА"),
    39:  ("football", "Англия. Премьер-лига"),
    140: ("football", "Испания. Ла Лига"),
    135: ("football", "Италия. Серия А"),
    78:  ("football", "Германия. Бундеслига"),
    61:  ("football", "Франция. Лига 1"),
    235: ("football", "Россия. Премьер-Лига"),  # РПЛ
}

# Fetch fixtures N days into the future
# Optimized: 2 days instead of 3 to reduce API calls (free plan: 100/day)
DAYS_AHEAD = 2


class ApiFootballParser(BaseParser):
    """API-Football v3 Parser"""

    def __init__(self):
        super().__init__("ApiFootball", BASE_URL)

    def _headers(self) -> Dict[str, str]:
        return {
            "x-apisports-key": API_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io",
        }

    async def _get(self, path: str, params: dict) -> Optional[dict]:
        """GET request to API-Football."""
        await self.init_session()
        url = f"{BASE_URL}{path}"
        try:
            async with self.session.get(url, headers=self._headers(), params=params, proxy=self.proxy) as r:
                if r.status != 200:
                    print(f"[ApiFootball] HTTP {r.status} for {path}")
                    return None
                return await r.json()
        except Exception as e:
            print(f"[ApiFootball] Request error {path}: {e}")
            return None

    async def _fetch_fixtures_by_date(self) -> List[dict]:
        """Fetch fixtures for the next DAYS_AHEAD days via date param (free-plan compatible).
        Filters results client-side to LEAGUES of interest.
        """
        today = datetime.now(tz=timezone.utc)
        all_fixtures: List[dict] = []
        league_ids = set(LEAGUES.keys())

        for offset in range(-2, DAYS_AHEAD + 1):
            date_str = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
            data = await self._get("/fixtures", {"date": date_str})
            for fix in (data or {}).get("response", []):
                if fix.get("league", {}).get("id") in league_ids:
                    all_fixtures.append(fix)

        # Also grab live fixtures
        live_data = await self._get("/fixtures", {"live": "all"})
        for fix in (live_data or {}).get("response", []):
            if fix.get("league", {}).get("id") in league_ids:
                all_fixtures.append(fix)

        return all_fixtures

    async def _fetch_odds(self, fixture_id: int) -> Optional[dict]:
        """Fetch pre-match odds for a fixture."""
        data = await self._get("/odds", {"fixture": fixture_id})
        responses = (data or {}).get("response", [])
        if not responses:
            return None
        return responses[0]

    def _parse_odds(self, odds_response: dict, match_data: dict):
        """Extract h2h / totals odds from the odds response."""
        bookmakers = (odds_response or {}).get("bookmakers", [])
        for bk in bookmakers:
            for bet in bk.get("bets", []):
                name = bet.get("name", "")
                values = bet.get("values", [])

                if name in ("Match Winner", "1X2"):
                    for v in values:
                        label = v.get("value", "")
                        odd = float(v.get("odd", 0) or 0)
                        if label in ("Home", "1"):
                            match_data["odds_1"] = odd
                        elif label in ("Draw", "X"):
                            match_data["odds_x"] = odd
                        elif label in ("Away", "2"):
                            match_data["odds_2"] = odd

                elif name in ("Goals Over/Under", "Over/Under"):
                    # Собираем все линии тоталов, предпочитая 2.5
                    best_over = None
                    best_under = None
                    best_val = None
                    fallback_over = None
                    fallback_under = None
                    fallback_val = None
                    for v in values:
                        label = v.get("value", "")
                        odd = float(v.get("odd", 0) or 0)
                        if label.startswith("Over"):
                            parts = label.split(" ", 1)
                            try:
                                raw = parts[1] if len(parts) > 1 else parts[0][4:]
                                if raw:
                                    line_val = float(raw)
                                    if line_val == 2.5:
                                        best_val = line_val
                                        best_over = odd
                                    elif fallback_val is None:
                                        fallback_val = line_val
                                        fallback_over = odd
                            except (IndexError, ValueError):
                                pass
                        elif label.startswith("Under"):
                            parts = label.split(" ", 1)
                            try:
                                raw = parts[1] if len(parts) > 1 else parts[0][5:]
                                if raw:
                                    line_val = float(raw)
                                    if line_val == 2.5:
                                        best_under = odd
                                    elif fallback_under is None:
                                        fallback_under = odd
                            except (IndexError, ValueError):
                                pass
                    
                    if best_val is not None:
                        match_data["total_value"] = best_val
                        match_data["total_over"] = best_over or 0.0
                        match_data["total_under"] = best_under or 0.0
                    elif fallback_val is not None:
                        match_data["total_value"] = fallback_val
                        match_data["total_over"] = fallback_over or 0.0
                        match_data["total_under"] = fallback_under or 0.0

    async def parse(self) -> List[Dict]:
        if not API_KEY:
            print("[ApiFootball] API_FOOTBALL_KEY not configured — skipping")
            return []

        # Fetch all fixtures via date-based query (free-plan compatible)
        fixtures = await self._fetch_fixtures_by_date()
        print(f"[ApiFootball] fetched {len(fixtures)} fixtures for target leagues")

        all_matches: List[Dict] = []
        seen_ids: set = set()

        for fixture in fixtures:
            f          = fixture.get("fixture", {})
            teams      = fixture.get("teams", {})
            league_obj = fixture.get("league", {})
            fixture_id = f.get("id")
            if not fixture_id or fixture_id in seen_ids:
                continue
            seen_ids.add(fixture_id)

            league_id   = league_obj.get("id")
            sport_type, league_name = LEAGUES.get(league_id, ("football", league_obj.get("name", "")))
            home        = teams.get("home", {}).get("name", "")
            away        = teams.get("away", {}).get("name", "")
            date_str    = f.get("date", "")
            status_long = f.get("status", {}).get("long", "")
            is_live     = status_long in ("First Half", "Second Half", "Halftime",
                                          "Extra Time", "Break Time", "Penalty In Progress")

            try:
                match_time = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                ).isoformat()
            except Exception:
                match_time = date_str

            score = None
            status_short = f.get("status", {}).get("short", "")
            if status_short in ("FT", "AET", "PEN"):
                goals = fixture.get("goals", {})
                h_goals = goals.get("home")
                a_goals = goals.get("away")
                if h_goals is not None and a_goals is not None:
                    score = f"{h_goals}:{a_goals}"

            match_data = {
                "external_id":       f"apifootball_{fixture_id}",
                "sport":             sport_type,
                "league":            league_name,
                "home_team":         home,
                "away_team":         away,
                "match_time":        match_time,
                "match_url":         f"https://www.api-football.com/fixture/{fixture_id}",
                "is_live":           is_live,
                "score":             score,
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

            odds_resp = await self._fetch_odds(fixture_id)
            if odds_resp:
                self._parse_odds(odds_resp, match_data)

            all_matches.append(match_data)

        print(f"[ApiFootball] {len(all_matches)} matches processed")
        return all_matches
