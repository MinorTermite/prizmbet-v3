#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automatic PRIZM payout for won bets via sendMoney API."""
from __future__ import annotations

import asyncio
import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


async def _ensure_db() -> None:
    if not db.initialized:
        db.init()
    if not db.initialized:
        raise RuntimeError("Supabase is not configured")


def _send_prizm(recipient: str, amount: float, message: str = "") -> dict[str, Any] | None:
    """Send PRIZM via prizm_api.send_money (shared helper)."""
    if not prizm_api.PASSPHRASE:
        log.error("PRIZM_PASSPHRASE is not set — cannot send payouts")
        return None
    result = prizm_api.send_money(recipient, amount, message)
    if not result:
        log.warning("sendMoney failed for %s amount=%.2f", recipient, amount)
    return result


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
        log.warning("[SKIP] Invalid payout data tx=%s wallet=%s amount=%.2f", tx_id[:18], sender_wallet, payout_amount)
        return False

    if payout_amount > AUTO_PAYOUT_MAX:
        log.info("[MANUAL] Payout %.2f exceeds auto limit %.0f — skipping tx=%s", payout_amount, AUTO_PAYOUT_MAX, tx_id[:18])
        return False

    # Check balance before sending.
    balance = await _check_balance_alert()
    if balance is not None and balance < payout_amount:
        log.warning("[INSUFFICIENT] Balance %.2f < payout %.2f — skipping tx=%s", balance, payout_amount, tx_id[:18])
        return False

    message = f"PrizmBet payout | bet {tx_id[:18]}"
    result = _send_prizm(sender_wallet, payout_amount, message=message)
    if not result:
        log.error("[FAIL] sendMoney failed for tx=%s amount=%.2f to %s", tx_id[:18], payout_amount, sender_wallet)
        return False

    payout_tx_id = str(result.get("transaction") or "")
    log.info("[PAID] tx=%s payout_tx=%s amount=%.2f to %s", tx_id[:18], payout_tx_id, payout_amount, sender_wallet)

    await db.mark_bet_paid(tx_id, payout_tx_id=payout_tx_id, payout_amount=payout_amount)

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


async def run_once() -> int:
    """Process all won bets that have not been paid yet. Returns count of payouts sent."""
    await _ensure_db()

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
