# -*- coding: utf-8 -*-
"""PrizmBet v3 configuration."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

    UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", "")
    UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN", "")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_NOTIFY_CHAT_IDS = os.getenv("TELEGRAM_NOTIFY_CHAT_IDS", "")
    V3_TELEGRAM_BOT_TOKEN = os.getenv("V3_TELEGRAM_BOT_TOKEN", "")
    V3_TELEGRAM_CHAT_ID = os.getenv("V3_TELEGRAM_CHAT_ID", "")
    V3_TELEGRAM_CHAT_IDS = os.getenv("V3_TELEGRAM_CHAT_IDS", "")
    V3_TELEGRAM_MIN_ALERT_PRIZM = float(os.getenv("V3_TELEGRAM_MIN_ALERT_PRIZM", "1000"))

    ADMIN_VIEW_KEY = os.getenv("ADMIN_VIEW_KEY", "")
    SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "").strip().lower()
    SUPER_ADMIN_LOGIN = os.getenv("SUPER_ADMIN_LOGIN", "owner").strip().lower()
    ADMIN_SESSION_HOURS = int(os.getenv("ADMIN_SESSION_HOURS", "12"))
    ADMIN_PASSWORD_ITERATIONS = int(os.getenv("ADMIN_PASSWORD_ITERATIONS", "260000"))

    GOOGLE_SHEETS_MIRROR_ENABLED = os.getenv("GOOGLE_SHEETS_MIRROR_ENABLED", "false").lower() == "true"
    GOOGLE_SHEETS_WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")
    GOOGLE_SHEETS_WEBHOOK_TOKEN = os.getenv("GOOGLE_SHEETS_WEBHOOK_TOKEN", "")

    ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
    ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY", "")
    PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
    PROXY_URL = os.getenv("PROXY_URL", "")
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    PINNACLE_LOGIN = os.getenv("PINNACLE_LOGIN", "")
    PINNACLE_PASSWORD = os.getenv("PINNACLE_PASSWORD", "")

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

    MIN_BET = float(os.getenv("MIN_BET", "10"))
    # Official PRIZM epoch from getConstants. Used for tx timestamp decoding.
    PRIZM_EPOCH = int(os.getenv("PRIZM_EPOCH", "1532715480"))


config = Config()
