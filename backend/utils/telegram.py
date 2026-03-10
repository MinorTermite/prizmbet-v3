# -*- coding: utf-8 -*-
"""Telegram Notifications"""
import asyncio
import aiohttp
from backend.config import config

class TelegramBot:
    """Telegram bot for notifications"""
    
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
    
    async def send_message(self, message: str, parse_mode="HTML"):
        """Send message to Telegram"""
        if not self.enabled:
            return False
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": message, "parse_mode": parse_mode}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def send_alert(self, title: str, message: str):
        """Send alert message"""
        formatted = f"<b>{title}</b>\n\n{message}"
        await self.send_message(formatted)

    async def send_alert_throttled(
        self,
        title: str,
        message: str,
        cooldown_key: str,
        cooldown_seconds: int = 1800,
    ):
        """Send alert, but skip if the same cooldown_key was sent recently."""
        from backend.utils.redis_client import cache

        redis_key = f"alert_throttle:{cooldown_key}"
        if await cache.get(redis_key):
            return False
        await self.send_alert(title, message)
        await cache.set(redis_key, "1", expire=cooldown_seconds)
        return True
    
    async def send_parser_report(self, parser_name: str, matches_count: int, status: str):
        """Send parser execution report"""
        emoji = "✅" if status == "success" else "❌"
        formatted = f"{emoji} <b>Parser: {parser_name}</b>\nStatus: {status}\nMatches: {matches_count}"
        await self.send_message(formatted)

telegram = TelegramBot()
