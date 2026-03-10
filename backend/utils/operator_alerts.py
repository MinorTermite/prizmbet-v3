# -*- coding: utf-8 -*-
"""Operator-facing alerts for processed intent bets."""
from __future__ import annotations

import logging
from typing import Any

from backend.utils.bet_views import build_bet_view, format_operator_telegram_message, load_matches_cache
from backend.utils.telegram import telegram

log = logging.getLogger(__name__)


async def notify_bet_processed(bet_row: dict[str, Any], intent: dict[str, Any] | None = None, match: dict[str, Any] | None = None) -> bool:
    """Send a decoded Telegram alert for a freshly processed bet."""
    if not telegram.enabled:
        return False
    try:
        view = build_bet_view(bet_row, intent=intent, match=match, match_cache=load_matches_cache())
        message = format_operator_telegram_message(view)
        return await telegram.send_message_many(message, parse_mode='HTML')
    except Exception as exc:
        log.warning('Operator notification failed: %s', exc)
        return False
