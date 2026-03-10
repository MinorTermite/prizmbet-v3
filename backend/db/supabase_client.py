# -*- coding: utf-8 -*-
"""Supabase Database Client"""
from datetime import datetime, timezone
from supabase import create_client
from backend.config import config


class Database:
    """Database client for Supabase"""

    def __init__(self):
        self.client = None
        self.initialized = False

    def init(self):
        """Initialize database connection"""
        if not self.initialized and config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.initialized = True
                print("Database connected")
            except Exception as e:
                print(f"Database connection failed: {e}")
                self.initialized = False

    async def insert_match(self, match_data: dict):
        """Insert a match into database"""
        if not self.initialized:
            return None
        try:
            # We use a copy to avoid mutating the original dict if we need to remove keys
            data = match_data.copy()
            try:
                response = self.client.table('matches').insert(data).execute()
                return response.data
            except Exception as e:
                err_str = str(e).lower()
                # If a column is missing, we try one more time without the common culprits
                if "column" in err_str:
                    problem_cols = ["external_id", "is_live", "score", "total_value", "total_over", "total_under", "handicap_1_value", "handicap_1", "handicap_2_value", "handicap_2"]
                    for col in problem_cols:
                        if col in err_str:
                            data.pop(col, None)
                    
                    try:
                        response = self.client.table('matches').insert(data).execute()
                        return response.data
                    except Exception:
                        # If it still fails, we just give up on this match record for the DB
                        # but we return None to allow the parser to continue locally
                        return None
                print(f"Error inserting match: {e}")
                return None
        except Exception as e:
            print(f"Unexpected error in insert_match: {e}")
            return None

    async def get_matches(self, sport='football', limit=100):
        """Get matches from database"""
        if not self.initialized:
            return []
        try:
            response = self.client.table('matches').select('*').eq('sport', sport).order('match_time', desc=False).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching matches: {e}")
            return []

    async def log_parser_run(self, parser_name: str, status: str, matches_count: int = 0, error_message: str = None):
        """Log parser execution"""
        if not self.initialized:
            return
        try:
            self.client.table('parser_logs').insert({
                'parser_name': parser_name,
                'status': status,
                'matches_count': matches_count,
                'error_message': error_message
            }).execute()
        except Exception as e:
            print(f"Error logging parser run: {e}")

    async def create_bet_intent(self, intent_hash: str, match_id: str, sender_wallet: str, outcome: str, odds_fixed: float, expires_at: str = None):
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
        r = self.client.table("bet_intents").select("*").eq("intent_hash", intent_hash).limit(1).execute().data
        return r[0] if r else None

    async def insert_bet(self, bet_row: dict):
        if not self.initialized:
            return None
        return self.client.table("bets").insert(bet_row).execute().data

    async def update_bet_status(self, tx_id: str, status: str, reason: str = None):
        if not self.initialized:
            return None
        payload = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if reason:
            payload["reject_reason"] = reason
        return self.client.table("bets").update(payload).eq("tx_id", tx_id).execute().data

    async def get_match_by_id(self, match_id: str):
        if not self.initialized:
            return None
        r = self.client.table("matches").select("id,match_time").eq("id", str(match_id)).limit(1).execute().data
        return r[0] if r else None

    async def get_listener_state(self):
        if not self.initialized:
            return None
        r = self.client.table("tx_listener_state").select("*").eq("id", 1).limit(1).execute().data
        return r[0] if r else None

    async def upsert_listener_state(self, last_prizm_timestamp: int, last_tx_id: str):
        if not self.initialized:
            return None
        row = {
            "id": 1,
            "last_prizm_timestamp": int(last_prizm_timestamp),
            "last_tx_id": last_tx_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return self.client.table("tx_listener_state").upsert(row).execute().data


db = Database()
