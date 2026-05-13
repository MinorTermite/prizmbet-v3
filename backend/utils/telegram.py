# -*- coding: utf-8 -*-
"""Telegram Notifications."""
import aiohttp
from backend.config import config


class TelegramBot:
    """Telegram bot for notifications."""

    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_ids = self._parse_chat_ids(
            config.TELEGRAM_CHAT_ID,
            config.TELEGRAM_NOTIFY_CHAT_IDS,
        )
        self.chat_id = self.chat_ids[0] if self.chat_ids else ''
        self.enabled = bool(self.token and self.chat_ids)

    @staticmethod
    def _parse_chat_ids(primary: str, extra: str) -> list[str]:
        values = []
        for candidate in [primary, *(extra or '').split(',')]:
            chat_id = str(candidate or '').strip()
            if chat_id and chat_id not in values:
                values.append(chat_id)
        return values

    async def send_message(self, message: str, parse_mode: str = 'HTML', chat_id: str | None = None):
        """Send message to a single Telegram chat."""
        target_chat = str(chat_id or self.chat_id or '').strip()
        if not self.token or not target_chat:
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            'chat_id': target_chat,
            'text': message,
            'parse_mode': parse_mode,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as response:
                    return response.status == 200
        except Exception:
            return False

    async def send_message_many(self, message: str, parse_mode: str = 'HTML', chat_ids: list[str] | None = None):
        """Broadcast a message to configured operator chats."""
        targets = chat_ids or self.chat_ids
        if not self.token or not targets:
            return False

        delivered = False
        for target in targets:
            delivered = await self.send_message(message, parse_mode=parse_mode, chat_id=target) or delivered
        return delivered

    async def send_alert(self, title: str, message: str):
        """Send alert message."""
        formatted = f"<b>{title}</b>\n\n{message}"
        await self.send_message(formatted)

    async def send_alert_throttled(self, title: str, message: str, cooldown_key: str, cooldown_seconds: int = 1800):
        """Send alert, but skip if the same cooldown_key was sent recently."""
        from backend.utils.redis_client import cache

        redis_key = f"alert_throttle:{cooldown_key}"
        if await cache.get(redis_key):
            return False
        await self.send_alert(title, message)
        await cache.set(redis_key, '1', expire=cooldown_seconds)
        return True

    async def send_parser_report(self, parser_name: str, matches_count: int, status: str):
        """Send parser execution report."""
        emoji = 'OK' if status == 'success' else 'FAIL'
        formatted = f"{emoji} <b>Parser: {parser_name}</b>\nStatus: {status}\nMatches: {matches_count}"
        await self.send_message(formatted)


telegram = TelegramBot()
