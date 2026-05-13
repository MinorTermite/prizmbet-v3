#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automatic PRIZM payout worker for won bets.

Current guarantees:
  - circuit breaker after repeated blockchain failures
  - 50 payouts/hour sliding window rate limit
  - emergency stop gate from app_config
  - DB idempotency via mark_bet_paid(status='won' AND payout_tx_id IS NULL)
  - payout reservations for in-flight transfers
  - append-only financial_events rows for pending/completed/failed lifecycle
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any
from uuid import uuid4

from backend.bot import prizm_api
from backend.config import config
from backend.db.supabase_client import db
from backend.utils.operator_alerts import notify_payout_sent
from backend.utils.operator_audit import log_operator_event
from backend.utils.telegram_v3 import telegram_v3

POLL_INTERVAL_SECONDS = 60
FETCH_LIMIT = 50
AUTO_PAYOUT_MAX = float(config.MAX_BET) * 10
LOW_BALANCE_THRESHOLD = 5000.0

CB_FAILURE_THRESHOLD = 5
CB_COOLDOWN_SECONDS = 1800

RATE_LIMIT_MAX = 50
RATE_LIMIT_WINDOW = 3600

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


class PayoutCircuitBreaker:
    """Simple CLOSED/OPEN/HALF_OPEN breaker for payout execution."""

    def __init__(self) -> None:
        self._failures = 0
        self._opened_at: float | None = None
        self._state = "CLOSED"

    @property
    def state(self) -> str:
        if self._state == "OPEN" and self._opened_at:
            if time.monotonic() - self._opened_at >= CB_COOLDOWN_SECONDS:
                self._state = "HALF_OPEN"
        return self._state

    @property
    def failures(self) -> int:
        return self._failures

    def is_open(self) -> bool:
        return self.state == "OPEN"

    def allow(self) -> bool:
        return self.state in {"CLOSED", "HALF_OPEN"}

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._state = "CLOSED"
        log.info("[CircuitBreaker] CLOSED - reset after success")

    def record_failure(self) -> None:
        self._failures += 1
        log.warning("[CircuitBreaker] failure #%d", self._failures)
        if self._state == "HALF_OPEN" or self._failures >= CB_FAILURE_THRESHOLD:
            self._state = "OPEN"
            self._opened_at = time.monotonic()
            log.error(
                "[CircuitBreaker] OPEN - %d consecutive failures. Payouts suspended for %d min.",
                self._failures,
                CB_COOLDOWN_SECONDS // 60,
            )


class _RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._calls: deque[float] = deque()

    def _trim(self) -> None:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > self._window:
            self._calls.popleft()

    def allow(self) -> bool:
        self._trim()
        if len(self._calls) >= self._max:
            return False
        self._calls.append(time.monotonic())
        return True

    @property
    def current_count(self) -> int:
        self._trim()
        return len(self._calls)


_circuit_breaker = PayoutCircuitBreaker()
_rate_limiter = _RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)


async def _ensure_db() -> None:
    if not db.initialized:
        db.init()
    if not db.initialized:
        raise RuntimeError("Supabase is not configured")


async def _check_balance_alert() -> float | None:
    info = prizm_api.get_balance()
    balance = info.get("balance")
    if balance is None:
        return None
    if balance < LOW_BALANCE_THRESHOLD and telegram_v3.enabled:
        await telegram_v3.send_message_many(
            (
                f"<b>Low balance alert</b>\n"
                f"Wallet: <code>{prizm_api.WALLET}</code>\n"
                f"Balance: <b>{balance:.2f} PRIZM</b>\n"
                f"Threshold: {LOW_BALANCE_THRESHOLD:.0f} PRIZM"
            ),
            parse_mode="HTML",
        )
    return float(balance)


async def _process_payout(bet: dict[str, Any]) -> bool:
    tx_id = str(bet.get("tx_id") or "")
    sender_wallet = str(bet.get("sender_wallet") or "").strip()
    payout_amount = float(bet.get("payout_amount") or 0)
    event_group_id = str(uuid4())

    if not sender_wallet or payout_amount <= 0:
        log.warning(
            "[SKIP] Invalid payout data tx=%s wallet=%s amount=%.2f",
            tx_id[:18],
            sender_wallet,
            payout_amount,
        )
        return False

    if await db.is_emergency_stop_enabled():
        log.error("[EMERGENCY_STOP] Auto-payout blocked for tx=%s", tx_id[:18])
        return False

    current = await db.get_bet_by_tx_id(tx_id)
    if not current:
        log.warning("[SKIP] Bet disappeared before payout tx=%s", tx_id[:18])
        return False

    current_status = str(current.get("status") or "").strip().lower()
    if current_status != "won" or current.get("payout_tx_id"):
        log.warning(
            "[SKIP] Bet state changed before payout tx=%s status=%s payout_tx_id=%s",
            tx_id[:18],
            current_status,
            current.get("payout_tx_id"),
        )
        return False

    if payout_amount > AUTO_PAYOUT_MAX:
        log.info(
            "[MANUAL] Payout %.2f exceeds auto limit %.0f - skipping tx=%s",
            payout_amount,
            AUTO_PAYOUT_MAX,
            tx_id[:18],
        )
        return False

    if not _circuit_breaker.allow():
        log.warning("[CIRCUIT_OPEN] Payouts suspended. tx=%s skipped.", tx_id[:18])
        return False

    if not _rate_limiter.allow():
        log.warning(
            "[RATE_LIMIT] Max %d payouts/hour reached - deferring tx=%s",
            RATE_LIMIT_MAX,
            tx_id[:18],
        )
        return False

    balance = await _check_balance_alert()
    if balance is not None and balance < payout_amount:
        log.warning(
            "[INSUFFICIENT] Balance %.2f < payout %.2f - skipping tx=%s",
            balance,
            payout_amount,
            tx_id[:18],
        )
        return False

    passphrase = await prizm_api.get_hot_passphrase()
    if not passphrase:
        log.error("[SKIP] Hot-wallet passphrase not configured - skipping tx=%s", tx_id[:18])
        return False

    reservation = await db.reserve_payout(
        tx_id,
        sender_wallet,
        payout_amount,
        reason="auto payout in progress",
        created_by="auto_payout",
    )
    if not reservation:
        log.error("[RESERVE_FAIL] Could not reserve payout for tx=%s", tx_id[:18])
        return False

    await db.insert_financial_event(
        {
            "event_group_id": event_group_id,
            "event_type": "payout",
            "direction": "outbound",
            "status": "pending",
            "wallet_from": prizm_api.WALLET,
            "wallet_to": sender_wallet,
            "amount_prizm": payout_amount,
            "bet_tx_id": tx_id,
            "initiated_by": "auto_payout",
            "details": {
                "reservation_id": reservation.get("id"),
                "breaker_state": _circuit_breaker.state,
                "rate_window_count": _rate_limiter.current_count,
            },
        }
    )

    message = f"1PrizmBet payout | bet {tx_id[:18]}"
    result = await prizm_api.send_money(sender_wallet, payout_amount, message)
    if not result:
        _circuit_breaker.record_failure()
        await db.release_payout_reservation(tx_id, reason="sendMoney failed")
        await db.insert_financial_event(
            {
                "event_group_id": event_group_id,
                "event_type": "payout",
                "direction": "outbound",
                "status": "failed",
                "wallet_from": prizm_api.WALLET,
                "wallet_to": sender_wallet,
                "amount_prizm": payout_amount,
                "bet_tx_id": tx_id,
                "initiated_by": "auto_payout",
                "error_message": "sendMoney returned empty result",
                "details": {"reservation_id": reservation.get("id")},
            }
        )
        log.error(
            "[FAIL] sendMoney failed for tx=%s amount=%.2f to %s",
            tx_id[:18],
            payout_amount,
            sender_wallet,
        )
        return False

    _circuit_breaker.record_success()

    payout_tx_id = str(result.get("transaction") or "")
    log.info(
        "[PAID] tx=%s payout_tx=%s amount=%.2f to %s",
        tx_id[:18],
        payout_tx_id,
        payout_amount,
        sender_wallet,
    )

    rows = await db.mark_bet_paid(tx_id, payout_tx_id=payout_tx_id, payout_amount=payout_amount)
    if not rows:
        log.warning(
            "[IDEMPOTENCY] mark_bet_paid returned no rows for tx=%s (already paid or status changed). payout_tx=%s sent.",
            tx_id[:18],
            payout_tx_id,
        )

    await db.consume_payout_reservation(
        tx_id,
        reason=f"completed via payout tx {payout_tx_id}" if payout_tx_id else "completed",
    )

    try:
        await db.insert_ledger_entry(
            {
                "tx_type": "payout",
                "bet_tx_id": tx_id,
                "prizm_tx_id": payout_tx_id,
                "wallet": sender_wallet,
                "amount_prizm": payout_amount,
                "fee_prizm": 0.05,
                "note": f"auto payout bet {tx_id[:18]}",
            }
        )
    except Exception as exc:
        log.warning("Ledger write failed for tx=%s: %s", tx_id[:18], exc)

    await db.insert_financial_event(
        {
            "event_group_id": event_group_id,
            "event_type": "payout",
            "direction": "outbound",
            "status": "completed" if rows else "manual_review",
            "wallet_from": prizm_api.WALLET,
            "wallet_to": sender_wallet,
            "amount_prizm": payout_amount,
            "bet_tx_id": tx_id,
            "prizm_tx_id": payout_tx_id,
            "initiated_by": "auto_payout",
            "details": {
                "reservation_id": reservation.get("id"),
                "db_guard_updated": bool(rows),
            },
            "error_message": None if rows else "mark_bet_paid returned no rows after blockchain send",
        }
    )

    await log_operator_event(
        "auto_payout",
        {**bet, "status": "paid", "payout_tx_id": payout_tx_id},
        extra={"payout_tx_id": payout_tx_id, "amount": payout_amount},
    )

    asyncio.create_task(
        notify_payout_sent(
            {**bet, "status": "paid", "payout_tx_id": payout_tx_id, "payout_amount": payout_amount},
        )
    )
    return True


async def run_once() -> int:
    await _ensure_db()

    if await db.is_emergency_stop_enabled():
        log.error("[EMERGENCY_STOP] Skipping auto-payout cycle")
        return 0

    if _circuit_breaker.is_open():
        log.warning("[CircuitBreaker] OPEN - skipping payout cycle")
        return 0

    bets = await db.get_bets_by_status(["won"], limit=FETCH_LIMIT)
    if not bets:
        return 0

    paid = 0
    for bet in bets:
        try:
            if await _process_payout(bet):
                paid += 1
        except Exception as exc:
            log.error("[ERROR] Payout failed for tx=%s: %s", str(bet.get("tx_id") or "")[:18], exc)
            _circuit_breaker.record_failure()
    return paid


async def main() -> None:
    log.info("Starting auto-payout loop for wallet %s", prizm_api.WALLET)
    while True:
        try:
            paid = await run_once()
            if paid:
                log.info("Auto-payout sent %d payout(s)", paid)
        except Exception as exc:
            log.error("Auto-payout loop error: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def get_runtime_status() -> dict[str, Any]:
    return {
        "circuit_breaker_state": _circuit_breaker.state,
        "consecutive_failures": _circuit_breaker.failures,
        "rate_limit_count": _rate_limiter.current_count,
        "rate_limit_max": RATE_LIMIT_MAX,
        "auto_payout_max": AUTO_PAYOUT_MAX,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "low_balance_threshold": LOW_BALANCE_THRESHOLD,
    }


def reset_runtime_guards() -> None:
    _circuit_breaker.record_success()


if __name__ == "__main__":
    asyncio.run(main())
