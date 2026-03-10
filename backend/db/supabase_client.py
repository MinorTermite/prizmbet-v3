# -*- coding: utf-8 -*-
"""Supabase Database Client."""
from datetime import datetime, timezone
from supabase import create_client
from backend.config import config


class Database:
    """Database client for Supabase."""

    def __init__(self):
        self.client = None
        self.initialized = False

    def init(self):
        """Initialize database connection."""
        if not self.initialized and config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.initialized = True
                print('Database connected')
            except Exception as e:
                print(f'Database connection failed: {e}')
                self.initialized = False

    async def insert_match(self, match_data: dict):
        if not self.initialized:
            return None
        try:
            data = match_data.copy()
            try:
                response = self.client.table('matches').insert(data).execute()
                return response.data
            except Exception as e:
                err_str = str(e).lower()
                if 'column' in err_str:
                    problem_cols = [
                        'external_id', 'is_live', 'score', 'total_value', 'total_over', 'total_under',
                        'handicap_1_value', 'handicap_1', 'handicap_2_value', 'handicap_2',
                    ]
                    for col in problem_cols:
                        if col in err_str:
                            data.pop(col, None)
                    try:
                        response = self.client.table('matches').insert(data).execute()
                        return response.data
                    except Exception:
                        return None
                print(f'Error inserting match: {e}')
                return None
        except Exception as e:
            print(f'Unexpected error in insert_match: {e}')
            return None

    async def get_matches(self, sport='football', limit=100):
        if not self.initialized:
            return []
        try:
            response = self.client.table('matches').select('*').eq('sport', sport).order('match_time', desc=False).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f'Error fetching matches: {e}')
            return []

    async def log_parser_run(self, parser_name: str, status: str, matches_count: int = 0, error_message: str = None):
        if not self.initialized:
            return
        try:
            self.client.table('parser_logs').insert({
                'parser_name': parser_name,
                'status': status,
                'matches_count': matches_count,
                'error_message': error_message,
            }).execute()
        except Exception as e:
            print(f'Error logging parser run: {e}')

    async def create_bet_intent(self, intent_hash: str, match_id: str, sender_wallet: str, outcome: str, odds_fixed: float, expires_at: str = None):
        if not self.initialized:
            return None
        payload = {
            'intent_hash': intent_hash,
            'match_id': str(match_id),
            'sender_wallet': sender_wallet,
            'outcome': outcome,
            'odds_fixed': round(float(odds_fixed), 2),
        }
        if expires_at:
            payload['expires_at'] = expires_at
        return self.client.table('bet_intents').insert(payload).execute().data

    async def get_bet_intent(self, intent_hash: str):
        if not self.initialized:
            return None
        response = self.client.table('bet_intents').select('*').eq('intent_hash', intent_hash).limit(1).execute().data
        return response[0] if response else None

    async def get_bet_intents_map(self, intent_hashes: list[str]):
        if not self.initialized:
            return {}
        cleaned = [str(item).strip().upper() for item in intent_hashes if str(item or '').strip()]
        if not cleaned:
            return {}
        try:
            response = self.client.table('bet_intents').select('*').in_('intent_hash', cleaned).execute().data
        except Exception as e:
            print(f'Error fetching bet intents: {e}')
            return {}
        return {str(row.get('intent_hash')).upper(): row for row in response if row.get('intent_hash')}

    async def insert_bet(self, bet_row: dict):
        if not self.initialized:
            return None
        return self.client.table('bets').insert(bet_row).execute().data

    async def get_recent_bets(self, limit: int = 100):
        if not self.initialized:
            return []
        try:
            response = self.client.table('bets').select('*').order('created_at', desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            print(f'Error fetching recent bets: {e}')
            return []

    async def update_bet_status(self, tx_id: str, status: str, reason: str = None):
        if not self.initialized:
            return None
        payload = {
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        if reason:
            payload['reject_reason'] = reason
        return self.client.table('bets').update(payload).eq('tx_id', tx_id).execute().data

    async def get_match_by_id(self, match_id: str):
        if not self.initialized:
            return None
        response = self.client.table('matches').select('id,match_time,team1,team2,league,sport').eq('id', str(match_id)).limit(1).execute().data
        return response[0] if response else None

    async def get_matches_map(self, match_ids: list[str]):
        if not self.initialized:
            return {}
        cleaned = [str(item).strip() for item in match_ids if str(item or '').strip()]
        if not cleaned:
            return {}
        try:
            response = self.client.table('matches').select('id,match_time,team1,team2,league,sport').in_('id', cleaned).execute().data
        except Exception as e:
            print(f'Error fetching match map: {e}')
            return {}
        return {str(row.get('id')): row for row in response if row.get('id')}

    async def get_listener_state(self):
        if not self.initialized:
            return None
        response = self.client.table('tx_listener_state').select('*').eq('id', 1).limit(1).execute().data
        return response[0] if response else None

    async def upsert_listener_state(self, last_prizm_timestamp: int, last_tx_id: str):
        if not self.initialized:
            return None
        row = {
            'id': 1,
            'last_prizm_timestamp': int(last_prizm_timestamp),
            'last_tx_id': last_tx_id,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        return self.client.table('tx_listener_state').upsert(row).execute().data


db = Database()
