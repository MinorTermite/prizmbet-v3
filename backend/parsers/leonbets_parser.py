#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leonbets JSON API Parser
API: https://leon.ru/api-2/betline/events/all
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from backend.parsers.base_parser import BaseParser

BASE_URL = "https://leon.ru"

# leon.ru sport family -> internal sport key
SPORTS_MAP = {
    "Soccer":      "football",
    "Basketball":  "basket",
    "IceHockey":   "hockey",
    "Tennis":      "tennis",
    "Volleyball":  "volleyball",
    "Baseball":    "baseball",
}


class LeonbetsParser(BaseParser):
    """Leonbets JSON API Parser"""

    def __init__(self):
        super().__init__("Leonbets", BASE_URL)

    async def parse(self) -> List[Dict]:
        """Parse matches from Leonbets"""
        await self.init_session()
        url = f"{BASE_URL}/api-2/betline/events/all"
        params = {"ctag": "ru-RU", "flags": "all"}
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://leon.ru/",
        }

        try:
            async with self.session.get(
                url, params=params, headers=headers, proxy=self.proxy
            ) as response:
                if response.status != 200:
                    print(f"[ERROR] Leonbets returned {response.status}")
                    return []

                data = await response.json()
                events = data.get("events", [])
                print(f"[Leonbets] total events from API: {len(events)}")

                matches = []
                for event in events:
                    match = self._parse_event(event)
                    if match:
                        matches.append(match)

                return matches

        except Exception as e:
            print(f"[ERROR] Leonbets: {e}")
            return []

    def _parse_event(self, event: Dict) -> Optional[Dict]:
        """Convert a Leonbets event dict to internal match format."""
        # Sport
        league_obj = event.get("league", {}) or {}
        sport_obj  = league_obj.get("sport", {}) or {}
        family     = sport_obj.get("family", "")
        sport_key  = SPORTS_MAP.get(family)
        if not sport_key:
            return None  # skip esports, virtual, etc.

        # Teams (use English nameDefault)
        name_default = event.get("nameDefault", "")
        parts = name_default.split(" - ", 1)
        if len(parts) != 2:
            return None
        home_team, away_team = parts[0].strip(), parts[1].strip()

        # League
        league_name = league_obj.get("nameDefault", "")
        region      = league_obj.get("regionDefault", "")
        if region and region.lower() not in league_name.lower():
            league_name = f"{region}. {league_name}"

        # Time
        kickoff    = event.get("kickoff", 0)
        match_time = None
        if kickoff:
            dt = datetime.fromtimestamp(kickoff / 1000, tz=timezone.utc)
            match_time = dt.isoformat()

        # Live flag
        is_live = (
            event.get("betline") == "inplay"
            or event.get("matchPhase") == "IN_PLAY"
        )

        match_data: Dict = {
            "external_id":       f"leon_{event.get('id', '')}",
            "sport":             sport_key,
            "league":            league_name,
            "home_team":         home_team,
            "away_team":         away_team,
            "match_time":        match_time,
            "is_live":           is_live,
            "match_url":         f"https://leon.ru{event.get('url', '')}",
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

        # Markets
        for market in event.get("markets", []):
            mname   = market.get("name", "") or ""
            runners = market.get("runners", [])

            # 1X2: name contains "1X2" or "1H2" (Cyrillic X sometimes), or runners are exactly 1, X, 2
            runner_names = {r.get("name", "") for r in runners}
            is_1x2 = ("1" in mname and ("X2" in mname.upper() or "\u04252" in mname.upper())) or \
                     ("1" in runner_names and "2" in runner_names and len(runner_names) <= 3)
            
            if is_1x2:
                for runner in runners:
                    rname = runner.get("name", "")
                    price = runner.get("price") or 0
                    if rname == "1":
                        match_data["odds_1"] = float(price)
                    elif rname in ("X", "x", "\u0425", "\u0445"):  # Latin or Cyrillic X
                        match_data["odds_x"] = float(price)
                    elif rname == "2":
                        match_data["odds_2"] = float(price)

            # Total — ищем конкретно линию 2.5
            elif "\u043e\u0442\u0430\u043b" in mname or "otal" in mname:
                best_over = None
                best_under = None
                best_val = None
                fallback_over = None
                fallback_under = None
                fallback_val = None
                for runner in runners:
                    rname = runner.get("name", "") or ""
                    price = runner.get("price") or 0
                    param = runner.get("param")
                    if param:
                        try:
                            pval = float(param)
                        except (TypeError, ValueError):
                            continue
                        is_over = "\u043e\u043b\u044c\u0448" in rname or "ver" in rname or rname == "\u0411"
                        is_under = "\u0435\u043d\u044c\u0448" in rname or "nder" in rname or rname == "\u041c"
                        if pval == 2.5:
                            if is_over:
                                best_over = float(price)
                                best_val = pval
                            elif is_under:
                                best_under = float(price)
                        else:
                            if is_over and fallback_val is None:
                                fallback_over = float(price)
                                fallback_val = pval
                            elif is_under and fallback_under is None:
                                fallback_under = float(price)
                
                if best_val is not None:
                    match_data["total_value"] = best_val
                    match_data["total_over"] = best_over or 0.0
                    match_data["total_under"] = best_under or 0.0
                elif fallback_val is not None:
                    match_data["total_value"] = fallback_val
                    match_data["total_over"] = fallback_over or 0.0
                    match_data["total_under"] = fallback_under or 0.0

            # Handicap
            elif "\u043e\u0440\u0430" in mname or "andicap" in mname or "\u0437\u0438\u0430\u0442\u0441\u043a" in mname:
                for runner in runners:
                    rname = runner.get("name", "") or ""
                    price = runner.get("price") or 0
                    param = runner.get("param")
                    if param:
                        try:
                            pval = float(param)
                        except (TypeError, ValueError):
                            continue
                        if rname == "1":
                            match_data["handicap_1_value"] = pval
                            match_data["handicap_1"]       = float(price)
                        elif rname == "2":
                            match_data["handicap_2_value"] = pval
                            match_data["handicap_2"]       = float(price)

        # No draw for tennis / basketball
        if sport_key in ("tennis", "basket"):
            match_data["odds_x"] = 0.0

        # Skip events with no odds
        if not match_data["odds_1"] and not match_data["odds_2"]:
            return None

        return match_data
