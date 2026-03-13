# -*- coding: utf-8 -*-
"""Operator-facing alerts for processed, settled and paid intent bets."""
from __future__ import annotations

import logging
from typing import Any

from backend.utils.bet_views import build_bet_view, format_operator_telegram_message, load_matches_cache
from backend.utils.telegram_v3 import telegram_v3

log = logging.getLogger(__name__)


def _resolve_amount(view: dict[str, Any], fallback: float = 0.0) -> float:
    for key in ("payout_amount_prizm", "potential_payout_prizm", "amount_prizm"):
        try:
            value = float(view.get(key) or 0)
            if value > 0:
                return value
        except Exception:
            continue
    return float(fallback or 0)


async def _send_view_message(message: str, amount: float) -> bool:
    if not telegram_v3.enabled or not telegram_v3.should_notify_amount(amount):
        return False
    return await telegram_v3.send_message_many(message, parse_mode="HTML")


async def notify_bet_processed(
    bet_row: dict[str, Any],
    intent: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
) -> bool:
    try:
        amount_prizm = float(bet_row.get("amount_prizm") or bet_row.get("amount") or 0)
    except Exception:
        amount_prizm = 0.0

    if not telegram_v3.enabled or not telegram_v3.should_notify_amount(amount_prizm):
        return False

    try:
        view = build_bet_view(bet_row, intent=intent, match=match, match_cache=load_matches_cache())
        message = format_operator_telegram_message(view)
        return await telegram_v3.send_message_many(message, parse_mode="HTML")
    except Exception as exc:
        log.warning("Operator notification failed: %s", exc)
        return False


async def notify_bet_settled(
    bet_row: dict[str, Any],
    intent: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
) -> bool:
    try:
        view = build_bet_view(bet_row, intent=intent, match=match, match_cache=load_matches_cache())
        header = "Ставка рассчитана" if view.get("status") == "won" else "Ставка завершена"
        amount = _resolve_amount(view, float(bet_row.get("amount_prizm") or 0))
        lines = [
            f"<b>{header}</b>",
            str(view.get("match_label") or "Матч без расшифровки"),
            f"Исход: <b>{view.get('outcome_label') or '—'}</b> @ <b>{view.get('odds_label') or '0.00'}</b>",
            f"Сумма: <b>{view.get('amount_label') or '0'} PRIZM</b>",
            f"Статус: <b>{view.get('status_label') or view.get('status') or '—'}</b>",
        ]
        if view.get("status") == "won":
            lines.append(f"К выплате: <b>{view.get('potential_payout_label') or '0'} PRIZM</b>")
        if view.get("score"):
            lines.append(f"Счёт: <b>{view.get('score')}</b>")
        if view.get("intent_hash"):
            lines.append(f"Код: <code>{view.get('intent_hash')}</code>")
        if view.get("tx_id"):
            lines.append(f"TX: <code>{view.get('tx_id')}</code>")
        if view.get("sender_wallet"):
            lines.append(f"Кошелёк: <code>{view.get('sender_wallet')}</code>")
        message = "\n".join(lines)
        return await _send_view_message(message, amount)
    except Exception as exc:
        log.warning("Settlement notification failed: %s", exc)
        return False


async def notify_payout_sent(
    bet_row: dict[str, Any],
    intent: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
) -> bool:
    try:
        view = build_bet_view(bet_row, intent=intent, match=match, match_cache=load_matches_cache())
        amount = _resolve_amount(view, float(bet_row.get("payout_amount") or 0))
        lines = [
            "<b>Выплата отправлена</b>",
            str(view.get("match_label") or "Матч без расшифровки"),
            f"Исход: <b>{view.get('outcome_label') or '—'}</b>",
            f"Выплата: <b>{view.get('potential_payout_label') or view.get('amount_label') or '0'} PRIZM</b>",
        ]
        if view.get("payout_tx_id"):
            lines.append(f"Payout TX: <code>{view.get('payout_tx_id')}</code>")
        if view.get("tx_id"):
            lines.append(f"Bet TX: <code>{view.get('tx_id')}</code>")
        if view.get("sender_wallet"):
            lines.append(f"Кошелёк: <code>{view.get('sender_wallet')}</code>")
        message = "\n".join(lines)
        return await _send_view_message(message, amount)
    except Exception as exc:
        log.warning("Payout notification failed: %s", exc)
        return False
