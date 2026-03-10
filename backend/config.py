# -*- coding: utf-8 -*-
"""PrizmBet v2 Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class"""
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Redis (Upstash)
    UPSTASH_REDIS_URL = os.getenv('UPSTASH_REDIS_URL', '')
    UPSTASH_REDIS_TOKEN = os.getenv('UPSTASH_REDIS_TOKEN', '')
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # API Keys — parsers
    ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')           # the-odds-api.com
    API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY', '')   # api-football.com (RapidAPI)
    ODDS_API_IO_KEY = os.getenv('ODDS_API_IO_KEY', '')     # odds-api.io
    PROXY_ENABLED = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
    PROXY_URL = os.getenv('PROXY_URL', '')
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
    
    # Pinnacle / ps3838 (Basic Auth)
    PINNACLE_LOGIN = os.getenv('PINNACLE_LOGIN', '')
    PINNACLE_PASSWORD = os.getenv('PINNACLE_PASSWORD', '')

    # GitHub
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

    # Betting / Tx Listener
    MIN_BET = float(os.getenv('MIN_BET', '10'))
    PRIZM_EPOCH = int(os.getenv('PRIZM_EPOCH', '1385294400'))

config = Config()
