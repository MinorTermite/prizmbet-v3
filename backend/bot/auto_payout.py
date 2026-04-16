#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automatic PRIZM payout for won bets via sendMoney API.

Features:
  - PayoutCircuitBreaker: stops auto-payouts after 5 consecutive failures
    (30-minute cooldown). Prevents runaway retries on blockchain errors.
  - Rate limiter: max 50 payouts per hour (sliding window).
  - Idempotency: mark_bet_paid() only updates bets with status='won' and
    payout_tx_id IS NULL (double-payout guard in DB layer).
  - Passphrase: loaded from DB (AES-256-GCM encrypted) via get_hot_passphrase(),
    NOT from module-level PASSPHRASE env var.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any

from backend.config import config
from backend.db.supabase_client import db
from backend.bot import prizm_api
from backend.utils.operator_audit import log_operator_event
from backend.utils.operator_alerts import notify_payout_sent
from backend.utils.telegram_v3 import telegram_v3

POLL_INTERVAL_SECONDS = 60
FETCH_LIMIT = 50
# Payouts above this threshold require manual operator confirmation.
AUTO_PAYOUT_MAX = float(config.MAX_BET) * 10
# Alert when wallet balance drops below this amount.
LOW_BALANCE_THRESHOLD = 5000.0

# Circuit breaker settings
CB_FAILURE_THRESHOLD = 5        # open after this many consecutive failures
CB_COOLDOWN_SECONDS  = 1800     # 30 minutes before half-open attempt

# Rate limiter: max 50 payouts per hour (sliding window)
RATE_LIMIT_MAX   = 50
RATE_LIMIT_WINDOW = 3600        # 1 hour in seconds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class PayoutCircuitBreaker:
    """Three-state circuit breaker: CLOSED → OPEN → HALF-OPEN → CLOSED.

    CLOSED   — normal operation, payouts allowed.
    OPEN     — breaker tripped (≥5 consecutive failures). Payouts blocked
               for CB_COOLDOWN_SECONDS to let the external system recover.
    HALF-OPEN — one test payout allowed after the cooldown expires. If it
               succeeds, the breaker resets to CLOSED. If it fails, the
               cooldown restarts.
    """

    def __init__(self) -> None:
        self._failures: int = 0
        self._opened_at: float | None = None
        self._state: str = "CLOSED"   # "CLOSED" | "OPEN" | "HALF_OPEN"

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            if self._opened_at and time.monotonic() - self._opened_at >= CB_COOLDOWN_SECONDS:
                self._state = "HALF_OPEN"
        return self._state

    def is_open(self) -> bool:
        return self.state == "OPEN"

    def allow(self) -> bool:
        """Returns True if a payout attempt should be allowed."""
        return self.state in ("CLOSED", "HALF_OPEN")

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._state = "CLOSED"
        log.info("[CircuitBreaker] CLOSED — reset after success")

    def record_failure(self) -> None:
        self._failures += 1
        log.warning("[CircuitBreaker] failure #%d", self._failures)
        if self._state == "HALF_OPEN" or self._failures >= CB_FAILURE_THRESHOLD:
            self._state = "OPEN"
            self._opened_at = time.monotonic()
            log.error(
                "[CircuitBreaker] OPEN — %d consecutive failures. "
                "Payouts suspended for %d min.",
                self._failures,
                CB_COOLDOWN_SECONDS // 60,
            )


# ---------------------------------------------------------------------------
# Rate limiter (sliding-window counter)
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._calls: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        # Drop entries older than the window
        while self._calls and now - self._calls[0] > self._window:
            self._calls.popleft()
        if len(self._calls) >= self._max:
            return False
        self._calls.append(now)
        return True


# Module-level singletons
_circuit_breaker = PayoutCircuitBreaker()
_rate_limiter    = _RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _ensure_db() -> None:
    if not db.initialized:
        db.init()
    if not db.initialized:
        raise RuntimeError("Supabase is not configured")


async def _check_balance_alert() -> float | None:
    """Check wallet balance and alert operator if it is low. Returns balance or None."""
    info = prizm_api.get_balance()
    balance = info.get("balance")
    if balance is None:
        return None

    if balance < LOW_BALANCE_THRESHOLD and telegram_v3.enabled:
        msg = (
            f"<b>Low balance alert</b>\n"
            f"Wallet: <code>{prizm_api.WALLET}</code>\n"
            f"Balance: <b>{balance:.2f} PRIZM</b>\n"
            f"Threshold: {LOW_BALANCE_THRESHOLD:.0f} PRIZM"
        )
        await telegram_v3.send_message_many(msg, parse_mode="HTML")

    return balance


async def _process_payout(bet: dict[str, Any]) -> bool:
    """Attempt to pay out a single won bet. Returns True on success."""
    tx_id = str(bet.get("tx_id") or "")
    sender_wallet = str(bet.get("sender_wallet") or "").strip()
    payout_amount = float(bet.get("payout_amount") or 0)

    if not sender_wallet or payout_amount <= 0:
        log.warning("[SKIP] Invalid payout data tx=%s wallet=%s amount=%.2f",
                    tx_id[:18], sender_wallet, payout_amount)
        return False

    if payout_amount > AUTO_PAYOUT_MAX:
        log.info("[MANUAL] Payout %.2f exceeds auto limit %.0f — skipping tx=%s",
                 payout_amount, AUTO_PAYOUT_MAX, tx_id[:18])
        return False

    # Circuit breaker gate
    if not _circuit_breaker.allow():
        log.warning("[CIRCUIT_OPEN] Payouts suspended. tx=%s skipped.", tx_id[:18])
        return False

    # Rate limiter gate
    if not _rate_limiter.allow():
        log.warning("[RATE_LIMIT] Max %d payouts/hour reached — deferring tx=%s",
                    RATE_LIMIT_MAX, tx_id[:18])
        return False

    # Check balance before sending.
    balance = await _check_balance_alert()
    if balance is not None and balance < payout_amount:
        log.warning("[INSUFFICIENT] Balance %.2f < payout %.2f — skipping tx=%s",
                    balance, payout_amount, tx_id[:18])
        return False

    # Early passphrase check — config errors must NOT trip the circuit breaker
    passphrase = await prizm_api.get_hot_passphrase()
    if not passphrase:
        log.error("[SKIP] Hot-wallet passphrase not configured — skipping tx=%s", tx_id[:18])
        return False

    message = f"PrizmBet payout | bet {tx_id[:18]}"
    result = await prizm_api.send_money(sender_wallet, payout_amount, message)
    if not result:
        _circuit_breaker.record_failure()
        log.error("[FAIL] sendMoney failed for tx=%s amount=%.2f to %s",
                  tx_id[:18], payout_amount, sender_wallet)
        return False

    _circuit_breaker.record_success()

    payout_tx_id = str(result.get("transaction") or "")
    log.info("[PAID] tx=%s payout_tx=%s amount=%.2f to %s",
             tx_id[:18], payout_tx_id, payout_amount, sender_wallet)

    rows = await db.mark_bet_paid(tx_id, payout_tx_id=payout_tx_id, payout_amount=payout_amount)
    if not rows:
        # DB guard fired — bet was already paid or status changed. Not a failure.
        log.warning("[IDEMPOTENCY] mark_bet_paid returned no rows for tx=%s "
                    "(already paid or status changed). payout_tx=%s sent.",
                    tx_id[:18], payout_tx_id)

    # Write ledger entry for the payout
    try:
        await db.insert_ledger_entry({
            "tx_type": "payout",
            "bet_tx_id": tx_id,
            "prizm_tx_id": payout_tx_id,
            "wallet": sender_wallet,
            "amount_prizm": payout_amount,
            "fee_prizm": 0.05,
            "note": f"auto payout bet {tx_id[:18]}",
        })
    except Exception as exc:
        log.warning("Ledger write failed for tx=%s: %s", tx_id[:18], exc)

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


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def run_once() -> int:
    """Process all won bets that have not been paid yet. Returns count of payouts sent."""
    await _ensure_db()

    if _circuit_breaker.is_open():
        log.warning("[CircuitBreaker] OPEN — skipping payout cycle")
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
            log.error("[ERROR] Payout failed for tx=%s: %s",
                      str(bet.get("tx_id") or "")[:18], exc)
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


if __name__ == "__main__":
    asyncio.run(main())
