#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pinnacle / ps3838 JSON API Parser
Docs: https://pinnacleapi.github.io/
Mirror: https://api.ps3838.com/v1/ (identical response format, no funded account required)
Auth: HTTP Basic (Base64-encoded "login:password")
"""

import base64
from datetime import datetime
from typing import List, Dict, Optional

from backend.config import config
from backend.parsers.base_parser import BaseParser

# Use ps3838 mirror — same response format, more accessible
BASE_URL = "https://api.ps3838.com/v1"

# Pinnacle sport IDs
SPORTS_MAP = {
    29: ("football", "Футбол"),
    18: ("basket",   "Баскетбол"),
    19: ("hockey",   "Хоккей"),
    33: ("tennis",   "Теннис"),
}


class PinnacleParser(BaseParser):
    """Pinnacle / ps3838 JSON API Parser"""

    def __init__(self):
        super().__init__("Pinnacle", BASE_URL)
        login = config.PINNACLE_LOGIN
        password = config.PINNACLE_PASSWORD
        raw = f"{login}:{password}".encode()
        self._auth_header = "Basic " + base64.b64encode(raw).decode()

    @property
    def _enabled(self) -> bool:
        return bool(config.PINNACLE_LOGIN and config.PINNACLE_PASSWORD)

    async def parse(self) -> List[Dict]:
        """Parse prematch odds from all supported sports"""
        if not self._enabled:
            print("[Pinnacle] Credentials not configured — skipping")
            return []

        all_matches: List[Dict] = []
        for sport_id, (sport_key, sport_label) in SPORTS_MAP.items():
            fixtures = await self._fetch_fixtures(sport_id)
            odds = await self._fetch_odds(sport_id)
            merged = self._merge(fixtures, odds, sport_key, sport_label)
            all_matches.extend(merged)
            print(f"  [Pinnacle] {sport_label}: {len(merged)} events")

        return all_matches

    # ------------------------------------------------------------------
    async def _get(self, path: str, params: dict = None) -> Optional[dict]:
        """Authenticated GET request to Pinnacle/ps3838 API"""
        await self.init_session()
        url = f"{BASE_URL}/{path}"
        headers = {
            "Authorization": self._auth_header,
            "Accept": "application/json",
        }
        try:
            async with self.session.get(url, params=params, headers=headers, proxy=self.proxy) as resp:
                if resp.status == 401:
                    print("[Pinnacle] 401 Unauthorized — check credentials")
                    return None
                if resp.status != 200:
                    print(f"[Pinnacle] {path}: HTTP {resp.status}")
                    return None
                return await resp.json()
        except Exception as e:
            print(f"[Pinnacle] {path}: {e}")
            return None

    async def _fetch_fixtures(self, sport_id: int) -> Dict[str, dict]:
        """Fetch fixtures (teams, start time) indexed by event_id"""
        data = await self._get("fixtures", {"sportId": sport_id, "isLive": 0})
        if not data:
            return {}
        result = {}
        for league in data.get("league", []):
            league_name = league.get("name", "")
            for event in league.get("events", []):
                eid = event.get("id")
                if eid:
                    result[eid] = {
                        "league": league_name,
                        "home": event.get("home", ""),
                        "away": event.get("away", ""),
                        "starts": event.get("starts", ""),
                    }
        return result

    async def _fetch_odds(self, sport_id: int) -> Dict[str, dict]:
        """Fetch moneyline + totals + spreads indexed by event_id"""
        data = await self._get(
            "odds",
            {"sportId": sport_id, "oddsFormat": "Decimal", "isLive": 0},
        )
        if not data:
            return {}
        result = {}
        for league in data.get("leagues", []):
            for event in league.get("matchups", []):
                eid = event.get("id")
                if not eid:
                    continue
                entry: Dict = {
                    "odds_1": 0.0, "odds_x": 0.0, "odds_2": 0.0,
                    "total_value": None, "total_over": 0.0, "total_under": 0.0,
                    "handicap_1_value": None, "handicap_1": 0.0,
                    "handicap_2_value": None, "handicap_2": 0.0,
                }
                for period in event.get("periods", []):
                    if period.get("number") != 0:
                        continue  # use full-match period only
                    ml = period.get("moneyline")
                    if ml:
                        entry["odds_1"] = float(ml.get("home", 0) or 0)
                        entry["odds_x"] = float(ml.get("draw", 0) or 0)
                        entry["odds_2"] = float(ml.get("away", 0) or 0)
                    totals = period.get("totals", [])
                    if totals:
                        t = totals[0]
                        pts = t.get("points")
                        entry["total_value"] = float(pts) if pts is not None else None
                        entry["total_over"] = float(t.get("over", 0) or 0)
                        entry["total_under"] = float(t.get("under", 0) or 0)
                    spreads = period.get("spreads", [])
                    if spreads:
                        s = spreads[0]
                        hdp = s.get("hdp")
                        entry["handicap_1_value"] = float(hdp) if hdp is not None else None
                        entry["handicap_1"] = float(s.get("home", 0) or 0)
                        entry["handicap_2_value"] = -float(hdp) if hdp is not None else None
                        entry["handicap_2"] = float(s.get("away", 0) or 0)
                result[eid] = entry
        return result

    def _merge(
        self,
        fixtures: Dict[str, dict],
        odds: Dict[str, dict],
        sport_key: str,
        sport_label: str,
    ) -> List[Dict]:
        """Merge fixture metadata with odds data"""
        matches = []
        for eid, fix in fixtures.items():
            o = odds.get(eid)
            if not o:
                continue

            # Parse ISO start time
            match_time = None
            starts = fix.get("starts", "")
            if starts:
                try:
                    dt = datetime.fromisoformat(starts.replace("Z", "+00:00"))
                    match_time = dt.isoformat()
                except Exception:
                    pass

            match: Dict = {
                "external_id": f"pinnacle_{eid}",
                "sport": sport_key,
                "league": fix["league"],
                "home_team": fix["home"],
                "away_team": fix["away"],
                "match_time": match_time,
                **o,
            }

            # No draw for non-football sports
            if sport_key in ("basket", "tennis"):
                match["odds_x"] = 0.0

            matches.append(match)
        return matches
