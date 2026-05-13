# -*- coding: utf-8 -*-
"""Dedicated Telegram notifier for PRIZMBET v3 operator events."""
from __future__ import annotations

import aiohttp

from backend.config import config


class TelegramV3Bot:
    """Dedicated v3 Telegram bot wrapper with its own token and chat list."""

    def __init__(self):
        self.token = config.V3_TELEGRAM_BOT_TOKEN
        self.chat_ids = self._parse_chat_ids(
            config.V3_TELEGRAM_CHAT_ID,
            config.V3_TELEGRAM_CHAT_IDS,
        )
        self.min_alert_prizm = float(config.V3_TELEGRAM_MIN_ALERT_PRIZM or 1000)
        self.enabled = bool(self.token and self.chat_ids)

    @staticmethod
    def _parse_chat_ids(primary: str, extra: str) -> list[str]:
        values: list[str] = []
        for candidate in [primary, *(extra or '').split(',')]:
            chat_id = str(candidate or '').strip()
            if chat_id and chat_id not in values:
                values.append(chat_id)
        return values

    def should_notify_amount(self, amount: float | int | str | None) -> bool:
        try:
            return float(amount or 0) >= self.min_alert_prizm
        except Exception:
            return False

    async def send_message(self, message: str, parse_mode: str = 'HTML', chat_id: str | None = None) -> bool:
        target_chat = str(chat_id or '').strip()
        if not target_chat:
            target_chat = self.chat_ids[0] if self.chat_ids else ''
        if not self.token or not target_chat:
            return False

        url = f'https://api.telegram.org/bot{self.token}/sendMessage'
        payload = {
            'chat_id': target_chat,
            'text': message,
            'parse_mode': parse_mode,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return response.status == 200
        except Exception:
            return False

    async def send_message_many(self, message: str, parse_mode: str = 'HTML') -> bool:
        if not self.token or not self.chat_ids:
            return False

        delivered = False
        for target_chat in self.chat_ids:
            delivered = await self.send_message(message, parse_mode=parse_mode, chat_id=target_chat) or delivered
        return delivered


telegram_v3 = TelegramV3Bot()