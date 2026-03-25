# -*- coding: utf-8 -*-
"""Supabase database client for PrizmBet v3."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import create_client

from backend.config import config
from backend.utils.bet_views import load_matches_cache


def _frontend_match_row(match_id: str):
    match = load_matches_cache().get(str(match_id).strip())
    if not match:
        return None
    return {
        "id": str(match.get("id") or ""),
        "match_time": match.get("match_time") or "",
        "team1": match.get("team1") or "",
        "team2": match.get("team2") or "",
        "league": match.get("league") or "",
        "sport": match.get("sport") or "",
        "is_live": bool(match.get("is_live")),
        "score": match.get("score") or "",
    }


class Database:
    def __init__(self):
        self.client = None
        self.initialized = False

    def init(self):
        if not self.initialized and config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.initialized = True
                print("Database connected")
            except Exception as exc:
                print(f"Database connection failed: {exc}")
                self.initialized = False

    async def insert_match(self, match_data: dict):
        if not self.initialized:
            return None
        try:
            data = dict(match_data or {})
            try:
                response = self.client.table("matches").insert(data).execute()
                return response.data
            except Exception as exc:
                err_str = str(exc).lower()
                if "column" in err_str:
                    problem_cols = [
                        "external_id",
                        "is_live",
                        "score",
                        "total_value",
                        "total_over",
                        "total_under",
                        "handicap_1_value",
                        "handicap_1",
                        "handicap_2_value",
                        "handicap_2",
                    ]
                    for col in problem_cols:
                        if col in err_str:
                            data.pop(col, None)
                    try:
                        response = self.client.table("matches").insert(data).execute()
                        return response.data
                    except Exception:
                        return None
                print(f"Error inserting match: {exc}")
                return None
        except Exception as exc:
            print(f"Unexpected error in insert_match: {exc}")
            return None

    async def get_matches(self, sport: str = "football", limit: int = 100):
        if not self.initialized:
            return []
        try:
            response = (
                self.client
                .table("matches")
                .select("*")
                .eq("sport", sport)
                .order("match_time", desc=False)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as exc:
            print(f"Error fetching matches: {exc}")
            return []

    async def log_parser_run(self, parser_name: str, status: str, matches_count: int = 0, error_message: str | None = None):
        if not self.initialized:
            return None
        try:
            return self.client.table("parser_logs").insert({
                "parser_name": parser_name,
                "status": status,
                "matches_count": matches_count,
                "error_message": error_message,
            }).execute().data
        except Exception as exc:
            print(f"Error logging parser run: {exc}")
            return None

    async def create_bet_intent(self, intent_hash: str, match_id: str, sender_wallet: str, outcome: str, odds_fixed: float, expires_at: str | None = None):
        if not self.initialized:
            return None
        payload = {
            "intent_hash": intent_hash,
            "match_id": str(match_id),
            "sender_wallet": sender_wallet,
            "outcome": outcome,
            "odds_fixed": round(float(odds_fixed), 2),
        }
        if expires_at:
            payload["expires_at"] = expires_at
        return self.client.table("bet_intents").insert(payload).execute().data

    async def get_bet_intent(self, intent_hash: str):
        if not self.initialized:
            return None
        try:
            response = self.client.table("bet_intents").select("*").eq("intent_hash", intent_hash).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching bet intent: {exc}")
            return None

    async def get_bet_intents_map(self, intent_hashes: list[str]):
        if not self.initialized:
            return {}
        cleaned = [str(item).strip().upper() for item in intent_hashes if str(item or "").strip()]
        if not cleaned:
            return {}
        try:
            response = self.client.table("bet_intents").select("*").in_("intent_hash", cleaned).execute().data
            return {str(row.get("intent_hash")).upper(): row for row in response if row.get("intent_hash")}
        except Exception as exc:
            print(f"Error fetching bet intents: {exc}")
            return {}

    async def get_active_wallet_intents(self, sender_wallet: str, as_of_iso: str):
        if not self.initialized:
            return []
        wallet = str(sender_wallet or '').strip().upper()
        if not wallet:
            return []
        try:
            response = (
                self.client
                .table("bet_intents")
                .select("*")
                .eq("sender_wallet", wallet)
                .gte("expires_at", as_of_iso)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            return response.data or []
        except Exception as exc:
            print(f"Error fetching active wallet intents: {exc}")
            return []

    async def get_bets_by_intent_hashes(self, intent_hashes: list[str]):
        if not self.initialized:
            return []
        cleaned = [str(item or '').strip().upper() for item in intent_hashes if str(item or '').strip()]
        if not cleaned:
            return []
        try:
            response = self.client.table("bets").select("*").in_("intent_hash", cleaned).execute()
            return response.data or []
        except Exception as exc:
            print(f"Error fetching bets by intent hashes: {exc}")
            return []

    async def insert_bet(self, bet_row: dict):
        if not self.initialized:
            return None
        try:
            return self.client.table("bets").insert(bet_row).execute().data
        except Exception as exc:
            print(f"Error inserting bet: {exc}")
            return None

    async def get_recent_bets(self, limit: int = 100):
        if not self.initialized:
            return []
        try:
            response = self.client.table("bets").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data or []
        except Exception as exc:
            print(f"Error fetching recent bets: {exc}")
            return []

    async def get_bets_by_status(self, statuses: list[str], limit: int = 100):
        if not self.initialized:
            return []
        cleaned = [str(item or "").strip().lower() for item in statuses if str(item or "").strip()]
        if not cleaned:
            return []
        try:
            response = (
                self.client
                .table("bets")
                .select("*")
                .in_("status", cleaned)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as exc:
            print(f"Error fetching bets by status: {exc}")
            return []

    async def get_bet_by_tx_id(self, tx_id: str):
        if not self.initialized:
            return None
        try:
            response = self.client.table("bets").select("*").eq("tx_id", tx_id).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching bet by tx_id: {exc}")
            return None

    async def update_bet_status(self, tx_id: str, status: str, reason: str | None = None):
        if not self.initialized:
            return None
        payload = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if reason:
            payload["reject_reason"] = reason
        try:
            return self.client.table("bets").update(payload).eq("tx_id", tx_id).execute().data
        except Exception as exc:
            print(f"Error updating bet status: {exc}")
            return None

    async def update_bet_settlement(self, tx_id: str, status: str, payout_amount: float = 0.0, reason: str | None = None):
        if not self.initialized:
            return None
        payload = {
            "status": status,
            "payout_amount": round(float(payout_amount or 0), 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "reject_reason": reason,
        }
        try:
            return self.client.table("bets").update(payload).eq("tx_id", tx_id).execute().data
        except Exception as exc:
            print(f"Error updating bet settlement: {exc}")
            return None

    async def mark_bet_paid(self, tx_id: str, payout_tx_id: str = "", payout_amount: float | None = None):
        if not self.initialized:
            return None
        payload: dict[str, Any] = {
            "status": "paid",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        payout_tx_id = str(payout_tx_id or "").strip()
        if payout_tx_id:
            payload["payout_tx_id"] = payout_tx_id
        if payout_amount is not None:
            payload["payout_amount"] = round(float(payout_amount or 0), 2)
        try:
            return self.client.table("bets").update(payload).eq("tx_id", tx_id).execute().data
        except Exception as exc:
            print(f"Error marking bet paid: {exc}")
            return None

    async def has_admin_users(self) -> bool:
        if not self.initialized:
            return False
        try:
            response = self.client.table("admin_users").select("id").limit(1).execute().data
            return bool(response)
        except Exception as exc:
            print(f"Error checking admin users: {exc}")
            return False

    async def get_admin_user_by_login(self, login: str):
        if not self.initialized:
            return None
        try:
            response = self.client.table("admin_users").select("*").eq("login", str(login).strip().lower()).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching admin user by login: {exc}")
            return None

    async def get_admin_user_by_email(self, email: str):
        if not self.initialized:
            return None
        try:
            response = self.client.table("admin_users").select("*").eq("email", str(email).strip().lower()).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching admin user by email: {exc}")
            return None

    async def get_admin_user_by_id(self, user_id: int | str):
        if not self.initialized:
            return None
        try:
            response = self.client.table("admin_users").select("*").eq("id", user_id).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching admin user by id: {exc}")
            return None

    async def list_admin_users(self):
        if not self.initialized:
            return []
        try:
            response = self.client.table("admin_users").select("id,login,email,role,is_active,created_at,last_login_at").order("created_at", desc=False).execute()
            return response.data or []
        except Exception as exc:
            print(f"Error listing admin users: {exc}")
            return []

    async def create_admin_user(self, user_row: dict):
        if not self.initialized:
            return None
        try:
            response = self.client.table("admin_users").insert(user_row).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error creating admin user: {exc}")
            return None

    async def update_admin_user(self, user_id: int | str, payload: dict):
        if not self.initialized:
            return None
        try:
            response = self.client.table("admin_users").update(payload).eq("id", user_id).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error updating admin user: {exc}")
            return None

    async def insert_admin_session(self, session_row: dict):
        if not self.initialized:
            return None
        try:
            return self.client.table("admin_sessions").insert(session_row).execute().data
        except Exception as exc:
            print(f"Error creating admin session: {exc}")
            return None

    async def get_admin_session(self, token_hash: str):
        if not self.initialized:
            return None
        try:
            response = self.client.table("admin_sessions").select("*").eq("token_hash", token_hash).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching admin session: {exc}")
            return None

    async def touch_admin_session(self, token_hash: str):
        if not self.initialized:
            return None
        try:
            payload = {"last_seen_at": datetime.now(timezone.utc).isoformat()}
            return self.client.table("admin_sessions").update(payload).eq("token_hash", token_hash).execute().data
        except Exception as exc:
            print(f"Error touching admin session: {exc}")
            return None

    async def delete_admin_session(self, token_hash: str):
        if not self.initialized:
            return None
        try:
            return self.client.table("admin_sessions").delete().eq("token_hash", token_hash).execute().data
        except Exception as exc:
            print(f"Error deleting admin session: {exc}")
            return None

    async def delete_expired_admin_sessions(self):
        if not self.initialized:
            return None
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            return self.client.table("admin_sessions").delete().lt("expires_at", now_iso).execute().data
        except Exception as exc:
            print(f"Error deleting expired admin sessions: {exc}")
            return None

    async def insert_operator_audit_log(self, audit_row: dict):
        if not self.initialized:
            return None
        try:
            return self.client.table("operator_audit_log").insert(audit_row).execute().data
        except Exception as exc:
            print(f"Error inserting operator audit log: {exc}")
            return None

    async def get_operator_audit_log(self, limit: int = 80):
        if not self.initialized:
            return []
        try:
            response = self.client.table("operator_audit_log").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data or []
        except Exception as exc:
            print(f"Error fetching operator audit log: {exc}")
            return []

    async def get_match_by_id(self, match_id: str):
        cache_row = _frontend_match_row(match_id)
        if self.initialized:
            try:
                response = self.client.table("matches").select("id,match_time,team1,team2,league,sport,is_live,score").eq("id", str(match_id)).limit(1).execute().data
                if response:
                    row = response[0]
                    if cache_row:
                        row.setdefault("is_live", cache_row.get("is_live"))
                        row.setdefault("score", cache_row.get("score"))
                    return row
            except Exception as exc:
                print(f"Error fetching match by id: {exc}")
        return cache_row

    async def get_matches_map(self, match_ids: list[str]):
        cleaned = [str(item).strip() for item in match_ids if str(item or "").strip()]
        if not cleaned:
            return {}

        rows: dict[str, Any] = {}
        if self.initialized:
            try:
                response = self.client.table("matches").select("id,match_time,team1,team2,league,sport,is_live,score").in_("id", cleaned).execute().data
                rows = {str(row.get("id")): row for row in response if row.get("id")}
            except Exception as exc:
                print(f"Error fetching match map: {exc}")

        cache = load_matches_cache()
        for match_id in cleaned:
            if match_id in rows:
                if match_id in cache:
                    rows[match_id].setdefault("is_live", bool(cache[match_id].get("is_live")))
                    rows[match_id].setdefault("score", cache[match_id].get("score") or "")
                continue
            cached = cache.get(match_id)
            if not cached:
                continue
            rows[match_id] = {
                "id": str(cached.get("id") or ""),
                "match_time": cached.get("match_time") or "",
                "team1": cached.get("team1") or "",
                "team2": cached.get("team2") or "",
                "league": cached.get("league") or "",
                "sport": cached.get("sport") or "",
                "is_live": bool(cached.get("is_live")),
                "score": cached.get("score") or "",
            }
        return rows

    async def get_listener_state(self):
        if not self.initialized:
            return None
        try:
            response = self.client.table("tx_listener_state").select("*").eq("id", 1).limit(1).execute().data
            return response[0] if response else None
        except Exception as exc:
            print(f"Error fetching listener state: {exc}")
            return None

    async def upsert_listener_state(self, last_prizm_timestamp: int, last_tx_id: str):
        if not self.initialized:
            return None
        row = {
            "id": 1,
            "last_prizm_timestamp": int(last_prizm_timestamp),
            "last_tx_id": last_tx_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            return self.client.table("tx_listener_state").upsert(row).execute().data
        except Exception as exc:
            print(f"Error upserting listener state: {exc}")
            return None


    async def get_app_config(self, key: str) -> str | None:
        """Fetch a single value from app_config by key. Returns None if not found."""
        if not self.initialized:
            return None
        try:
            rows = self.client.table("app_config").select("value").eq("key", key).limit(1).execute().data
            return rows[0]["value"] if rows else None
        except Exception as exc:
            print(f"Error fetching app_config key={key}: {exc}")
            return None

    async def set_app_config(self, key: str, value: str) -> bool:
        """Upsert a key/value pair in app_config. Returns True on success."""
        if not self.initialized:
            return False
        try:
            from datetime import datetime, timezone
            self.client.table("app_config").upsert({
                "key": key,
                "value": value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            return True
        except Exception as exc:
            print(f"Error setting app_config key={key}: {exc}")
            return False


db = Database()
