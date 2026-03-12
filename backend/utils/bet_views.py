# -*- coding: utf-8 -*-
"""Helpers for decoding intent-based bets into operator-friendly views."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MATCHES_PATH = Path(__file__).resolve().parents[2] / "frontend" / "matches.json"

OUTCOME_LABELS = {
    "P1": "П1",
    "1": "П1",
    "Рџ1": "П1",
    "X": "X",
    "P2": "П2",
    "2": "П2",
    "Рџ2": "П2",
    "1X": "1X",
    "12": "12",
    "X2": "X2",
}

STATUS_LABELS = {
    "pending": "В ожидании",
    "awaiting_payment": "Ждёт перевод",
    "accepted": "Принята",
    "rejected": "Отклонена",
    "expired": "Истекла",
    "won": "Выиграла",
    "lost": "Проиграла",
    "refund_pending": "Ждёт возврат",
    "refunded": "Возвращена",
    "paid": "Выплачена",
}

REJECT_LABELS = {
    "INVALID_INTENT": "Код ставки не найден",
    "DUST_DONATION": "Сумма ниже минимальной ставки",
    "SENDER_MISMATCH": "Кошелёк отправителя не совпал с купоном",
    "INTENT_EXPIRED": "Купон просрочен",
    "MATCH_NOT_FOUND": "Матч не найден в актуальном кэше",
    "LATE_BET": "Ставка пришла после безопасного окна",
}

ACCEPTED_STATUSES = {"accepted", "won", "lost", "paid", "refunded", "refund_pending"}

_MATCH_CACHE_MTIME: float | None = None
_MATCH_CACHE_DATA: dict[str, dict[str, Any]] = {}


def load_matches_cache() -> dict[str, dict[str, Any]]:
    global _MATCH_CACHE_MTIME, _MATCH_CACHE_DATA
    if not MATCHES_PATH.exists():
        return {}
    try:
        mtime = MATCHES_PATH.stat().st_mtime
        if _MATCH_CACHE_MTIME == mtime and _MATCH_CACHE_DATA:
            return _MATCH_CACHE_DATA
        payload = json.loads(MATCHES_PATH.read_text(encoding="utf-8"))
        _MATCH_CACHE_DATA = {str(match.get("id")): match for match in payload.get("matches", []) if match.get("id")}
        _MATCH_CACHE_MTIME = mtime
    except Exception:
        return _MATCH_CACHE_DATA or {}
    return _MATCH_CACHE_DATA


def normalize_outcome_label(outcome: Any) -> str:
    raw = str(outcome or "").strip().upper()
    return OUTCOME_LABELS.get(raw, raw or "—")


def format_decimal(value: Any) -> str:
    try:
        number = float(value)
    except Exception:
        return "0.00"
    return f"{number:.2f}"


def format_prizm(value: Any) -> str:
    try:
        number = float(value)
    except Exception:
        return "0"
    return f"{number:,.2f}".replace(",", " ").rstrip("0").rstrip(".")


def shorten_identifier(value: Any, keep: int = 8) -> str:
    text = str(value or "").strip()
    if len(text) <= keep:
        return text or "—"
    return f"{text[:keep]}…{text[-4:]}"


def status_label(status: Any) -> str:
    raw = str(status or "").strip().lower()
    return STATUS_LABELS.get(raw, raw or "—")


def status_tone(status: Any) -> str:
    raw = str(status or "").strip().lower()
    if raw in {"accepted", "won", "paid"}:
        return "good"
    if raw in {"rejected", "lost", "expired"}:
        return "bad"
    if raw in {"refund_pending", "refunded"}:
        return "warn"
    return "neutral"


def reject_label(reason: Any) -> str:
    raw = str(reason or "").strip().upper()
    return REJECT_LABELS.get(raw, raw or "—")


def format_match_label(match: dict[str, Any] | None, match_id: Any) -> str:
    match = match or {}
    team1 = str(match.get("team1") or "").strip()
    team2 = str(match.get("team2") or "").strip()
    if team1 or team2:
        return " — ".join([part for part in (team1, team2) if part])
    match_id_text = str(match_id or "").strip()
    return f"Матч #{match_id_text}" if match_id_text else "Матч без ID"


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def describe_match_state(match: dict[str, Any] | None) -> dict[str, str]:
    match = match or {}
    score = str(match.get("score") or "").strip()
    if score:
        return {"state": "finished", "label": f"Завершён • {score}", "tone": "good"}

    if bool(match.get("is_live")):
        return {"state": "live", "label": "LIVE", "tone": "warn"}

    match_time = _parse_dt(match.get("match_time"))
    if not match_time:
        return {"state": "unknown", "label": "Время не определено", "tone": "neutral"}

    now = datetime.now(timezone.utc)
    kickoff = match_time.astimezone(timezone.utc)
    diff_minutes = int((kickoff - now).total_seconds() // 60)

    if 0 < diff_minutes <= 15:
        return {"state": "imminent", "label": "Старт < 15 мин", "tone": "warn"}
    if diff_minutes <= 0:
        return {"state": "post_start", "label": "После старта", "tone": "warn"}
    return {"state": "scheduled", "label": "До старта", "tone": "neutral"}


def build_bet_view(
    bet: dict[str, Any],
    intent: dict[str, Any] | None = None,
    match: dict[str, Any] | None = None,
    match_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    intent = intent or {}
    bet = bet or {}
    match_id = str(bet.get("match_id") or intent.get("match_id") or "").strip()
    source_match = match or {}
    if not source_match and match_id:
        source_match = (match_cache or load_matches_cache()).get(match_id, {})

    tx_id = str(bet.get("tx_id") or "").strip()
    intent_hash = str(bet.get("intent_hash") or intent.get("intent_hash") or "").strip().upper()
    sender_wallet = str(bet.get("sender_wallet") or intent.get("sender_wallet") or "").strip().upper()
    status = str(bet.get("status") or "pending").strip().lower()
    reject_reason = str(bet.get("reject_reason") or "").strip().upper()
    outcome_raw = str(intent.get("outcome") or bet.get("outcome") or "").strip().upper()
    outcome_label = normalize_outcome_label(outcome_raw)
    odds_fixed = round(float(bet.get("odds_fixed") or intent.get("odds_fixed") or 0), 2)
    amount_prizm = round(float(bet.get("amount_prizm") or bet.get("amount") or 0), 2)
    potential_payout = round(amount_prizm * odds_fixed, 2) if amount_prizm and odds_fixed else 0.0
    match_label = format_match_label(source_match, match_id)
    league = str(source_match.get("league") or "").strip()
    sport = str(source_match.get("sport") or "").strip()
    match_time = source_match.get("match_time") or ""
    block_timestamp = bet.get("block_timestamp") or ""
    created_at = bet.get("created_at") or block_timestamp or ""
    payout_tx_id = str(bet.get("payout_tx_id") or "").strip()
    match_state = describe_match_state(source_match)
    decoded_coupon = f"{match_label} • {outcome_label} @ {format_decimal(odds_fixed)}"
    operator_summary = f"{decoded_coupon} • {format_prizm(amount_prizm)} PRIZM"

    return {
        "tx_id": tx_id,
        "tx_short": shorten_identifier(tx_id, 14),
        "intent_hash": intent_hash,
        "intent_short": shorten_identifier(intent_hash, 10),
        "match_id": match_id,
        "match_label": match_label,
        "league": league,
        "sport": sport,
        "match_time": match_time,
        "sender_wallet": sender_wallet,
        "wallet_short": shorten_identifier(sender_wallet, 16),
        "outcome": outcome_raw or "",
        "outcome_label": outcome_label,
        "odds_fixed": odds_fixed,
        "odds_label": format_decimal(odds_fixed),
        "amount_prizm": amount_prizm,
        "amount_label": format_prizm(amount_prizm),
        "potential_payout_prizm": potential_payout,
        "potential_payout_label": format_prizm(potential_payout),
        "status": status,
        "status_label": status_label(status),
        "status_tone": status_tone(status),
        "reject_reason": reject_reason,
        "reject_label": reject_label(reject_reason) if reject_reason else "",
        "block_timestamp": block_timestamp,
        "created_at": created_at,
        "payout_tx_id": payout_tx_id,
        "decoded_coupon": decoded_coupon,
        "operator_summary": operator_summary,
        "operator_caption": f"Код {intent_hash or '—'} • {status_label(status)}",
        "score": str(source_match.get("score") or "").strip(),
        "match_state": match_state["state"],
        "match_state_label": match_state["label"],
        "match_state_tone": match_state["tone"],
    }


def search_blob(view: dict[str, Any]) -> str:
    pieces = [
        view.get("tx_id", ""),
        view.get("intent_hash", ""),
        view.get("sender_wallet", ""),
        view.get("match_id", ""),
        view.get("match_label", ""),
        view.get("league", ""),
        view.get("sport", ""),
        view.get("outcome_label", ""),
        view.get("status_label", ""),
        view.get("reject_label", ""),
        view.get("match_state_label", ""),
    ]
    return " ".join(str(piece or "").casefold() for piece in pieces)


def format_operator_telegram_message(view: dict[str, Any]) -> str:
    header = "Новая ставка принята" if view.get("status") == "accepted" else "Ставка обработана"
    if view.get("status") == "rejected":
        header = "Ставка отклонена"
    elif view.get("status") == "refund_pending":
        header = "Ставка ждёт возврат"

    lines = [
        f"<b>{html.escape(header)}</b>",
        html.escape(str(view.get("match_label") or "Матч без расшифровки")),
        f"Исход: <b>{html.escape(str(view.get('outcome_label') or '—'))}</b> @ <b>{html.escape(str(view.get('odds_label') or '0.00'))}</b>",
        f"Сумма: <b>{html.escape(str(view.get('amount_label') or '0'))} PRIZM</b>",
        f"Состояние матча: <b>{html.escape(str(view.get('match_state_label') or '—'))}</b>",
    ]
    if view.get("intent_hash"):
        lines.append(f"Код: <code>{html.escape(str(view['intent_hash']))}</code>")
    if view.get("sender_wallet"):
        lines.append(f"Кошелёк: <code>{html.escape(str(view['sender_wallet']))}</code>")
    if view.get("tx_id"):
        lines.append(f"TX: <code>{html.escape(str(view['tx_id']))}</code>")
    if view.get("status_label"):
        lines.append(f"Статус: <b>{html.escape(str(view['status_label']))}</b>")
    if view.get("reject_label"):
        lines.append(f"Причина: <b>{html.escape(str(view['reject_label']))}</b>")
    if view.get("league"):
        lines.append(f"Лига: {html.escape(str(view['league']))}")
    return "\n".join(lines)
