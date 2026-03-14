# -*- coding: utf-8 -*-
"""Operator audit log and optional Google Sheets mirror."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.config import config
from backend.db.supabase_client import db
from backend.utils.bet_views import build_bet_view, load_matches_cache

log = logging.getLogger(__name__)


def _coerce_float(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _build_payload(
    event_type: str,
    bet_row: dict[str, Any],
    intent: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
    reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    view = build_bet_view(bet_row, intent=intent, match=match, match_cache=load_matches_cache())
    payload = {
        "event_type": event_type,
        "tx_id": str(bet_row.get("tx_id") or "").strip(),
        "intent_hash": str((intent or {}).get("intent_hash") or bet_row.get("intent_hash") or "").strip().upper(),
        "match_id": str((intent or {}).get("match_id") or bet_row.get("match_id") or "").strip(),
        "status": str(bet_row.get("status") or "").strip().lower(),
        "sender_wallet": str(bet_row.get("sender_wallet") or "").strip().upper(),
        "amount_prizm": _coerce_float(bet_row.get("amount_prizm")),
        "odds_fixed": _coerce_float(bet_row.get("odds_fixed")),
        "payout_amount_prizm": _coerce_float(bet_row.get("payout_amount") or view.get("potential_payout_prizm")),
        "match_label": str(view.get("match_label") or ""),
        "operator_summary": str(view.get("operator_summary") or ""),
        "status_label": str(view.get("status_label") or ""),
        "match_state": str(view.get("match_state") or ""),
        "match_state_label": str(view.get("match_state_label") or ""),
        "reject_reason": str(reason or bet_row.get("reject_reason") or "").strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload["extra"] = _json_safe(extra)
    return _json_safe(payload)


def _post_json(url: str, payload: dict[str, Any], token: str = "") -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    if token:
        headers["X-Audit-Token"] = token
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=10) as response:
        response.read()


async def mirror_operator_event(payload: dict[str, Any]) -> bool:
    if not config.GOOGLE_SHEETS_MIRROR_ENABLED or not config.GOOGLE_SHEETS_WEBHOOK_URL:
        return False
    envelope = {
        "source": "prizmbet_v3",
        "event": payload,
    }
    try:
        await asyncio.to_thread(
            _post_json,
            config.GOOGLE_SHEETS_WEBHOOK_URL,
            envelope,
            str(config.GOOGLE_SHEETS_WEBHOOK_TOKEN or "").strip(),
        )
        return True
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        log.warning("Google Sheets mirror failed: %s", exc)
        return False


async def log_operator_event(
    event_type: str,
    bet_row: dict[str, Any],
    intent: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
    reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _build_payload(event_type, bet_row, intent=intent, match=match, reason=reason, extra=extra)
    audit_row = {
        "event_type": payload["event_type"],
        "tx_id": payload["tx_id"] or None,
        "intent_hash": payload["intent_hash"] or None,
        "match_id": payload["match_id"] or None,
        "status": payload["status"] or None,
        "sender_wallet": payload["sender_wallet"] or None,
        "amount_prizm": payload["amount_prizm"],
        "payload": payload,
        "created_at": payload["created_at"],
    }
    await db.insert_operator_audit_log(audit_row)
    await mirror_operator_event(payload)
    return payload
