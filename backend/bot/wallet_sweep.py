#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cold-storage sweep for the hot PRIZM wallet.

Sprint 1 hardening added here:
  - emergency stop gate
  - awareness of pending and reserved payouts
  - append-only financial_events lifecycle rows
  - correct prizm_ledger tx_type for sweep movements
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from uuid import uuid4

from backend.bot import prizm_api
from backend.db.supabase_client import db
from backend.utils.telegram_v3 import telegram_v3

POLL_INTERVAL_SECONDS = 600
SWEEP_THRESHOLD = float(os.getenv("PRIZM_SWEEP_THRESHOLD", "300000"))
SWEEP_MIN_KEEP = float(os.getenv("PRIZM_SWEEP_MIN_KEEP", "50000"))
COLD_WALLET = os.getenv("PRIZM_COLD_WALLET", "").strip()

log = logging.getLogger(__name__)


async def _ensure_db() -> None:
    if not db.initialized:
        db.init()


async def _notify(msg: str) -> None:
    try:
        if telegram_v3.enabled:
            await telegram_v3.send_message_many(msg, parse_mode="HTML")
    except Exception as exc:
        log.warning("Telegram notify failed: %s", exc)


async def sweep_once() -> dict[str, Any] | None:
    await _ensure_db()

    if await db.is_emergency_stop_enabled():
        log.error("[EMERGENCY_STOP] Sweep blocked by finance_emergency_stop flag")
        return None

    if not COLD_WALLET:
        log.debug("[Sweep] PRIZM_COLD_WALLET not set - sweep disabled")
        return None

    info = prizm_api.get_balance()
    balance = info.get("balance")
    if balance is None:
        log.warning("[Sweep] Could not fetch hot-wallet balance")
        return None
    balance = float(balance)

    if balance <= SWEEP_THRESHOLD:
        return None

    pending_total = await db.get_pending_payout_total()
    reserved_total = await db.get_reserved_payout_total()
    protected_keep = max(SWEEP_MIN_KEEP, pending_total, reserved_total)
    sweep_amount = round(balance - protected_keep, 2)

    if sweep_amount <= 0:
        log.warning(
            "[Sweep] Balance %.2f above threshold but protected keep %.2f leaves nothing to sweep",
            balance,
            protected_keep,
        )
        return None

    event_group_id = str(uuid4())
    await db.insert_financial_event(
        {
            "event_group_id": event_group_id,
            "event_type": "sweep",
            "direction": "internal",
            "status": "pending",
            "wallet_from": prizm_api.WALLET,
            "wallet_to": COLD_WALLET,
            "amount_prizm": sweep_amount,
            "balance_before": balance,
            "initiated_by": "wallet_sweep",
            "details": {
                "threshold": SWEEP_THRESHOLD,
                "min_keep": SWEEP_MIN_KEEP,
                "pending_payout_total": pending_total,
                "reserved_payout_total": reserved_total,
                "protected_keep": protected_keep,
            },
        }
    )

    log.info(
        "[Sweep] Balance %.2f > %.0f threshold -> sweeping %.2f PRIZM to %s (protected keep %.2f)",
        balance,
        SWEEP_THRESHOLD,
        sweep_amount,
        COLD_WALLET,
        protected_keep,
    )

    await _notify(
        (
            f"<b>Cold Storage Sweep</b>\n"
            f"Hot balance: <b>{balance:.2f} PRIZM</b>\n"
            f"Reserved payouts: <b>{reserved_total:.2f} PRIZM</b>\n"
            f"Pending won payouts: <b>{pending_total:.2f} PRIZM</b>\n"
            f"Sweeping: <b>{sweep_amount:.2f} PRIZM</b>\n"
            f"To cold: <code>{COLD_WALLET}</code>"
        )
    )

    result = await prizm_api.send_money(
        recipient=COLD_WALLET,
        amount=sweep_amount,
        message="1PrizmBet cold-storage sweep",
    )

    if not result or not result.get("transaction"):
        log.error("[Sweep] FAILED to sweep %.2f PRIZM to %s", sweep_amount, COLD_WALLET)
        await db.insert_financial_event(
            {
                "event_group_id": event_group_id,
                "event_type": "sweep",
                "direction": "internal",
                "status": "failed",
                "wallet_from": prizm_api.WALLET,
                "wallet_to": COLD_WALLET,
                "amount_prizm": sweep_amount,
                "balance_before": balance,
                "initiated_by": "wallet_sweep",
                "error_message": "sendMoney returned empty result",
                "details": {
                    "threshold": SWEEP_THRESHOLD,
                    "min_keep": SWEEP_MIN_KEEP,
                    "pending_payout_total": pending_total,
                    "reserved_payout_total": reserved_total,
                    "protected_keep": protected_keep,
                },
            }
        )
        await _notify(
            f"<b>Sweep FAILED</b>\nAmount: {sweep_amount:.2f} PRIZM\nCold: <code>{COLD_WALLET}</code>\nCheck logs."
        )
        return result

    tx_id = str(result["transaction"])
    balance_after = round(balance - sweep_amount, 2)
    log.info("[Sweep] SUCCESS tx=%s amount=%.2f PRIZM swept to %s", tx_id, sweep_amount, COLD_WALLET)

    try:
        await db.insert_ledger_entry(
            {
                "tx_type": "sweep",
                "prizm_tx_id": tx_id,
                "wallet": COLD_WALLET,
                "amount_prizm": sweep_amount,
                "fee_prizm": 0.05,
                "balance_after": balance_after,
                "note": "cold-storage sweep",
            }
        )
    except Exception as exc:
        log.warning("[Sweep] Ledger write failed: %s", exc)

    await db.insert_financial_event(
        {
            "event_group_id": event_group_id,
            "event_type": "sweep",
            "direction": "internal",
            "status": "completed",
            "wallet_from": prizm_api.WALLET,
            "wallet_to": COLD_WALLET,
            "amount_prizm": sweep_amount,
            "prizm_tx_id": tx_id,
            "balance_before": balance,
            "balance_after": balance_after,
            "initiated_by": "wallet_sweep",
            "details": {
                "threshold": SWEEP_THRESHOLD,
                "min_keep": SWEEP_MIN_KEEP,
                "pending_payout_total": pending_total,
                "reserved_payout_total": reserved_total,
                "protected_keep": protected_keep,
            },
        }
    )

    await _notify(
        (
            f"<b>Sweep Completed</b>\n"
            f"TX: <code>{tx_id}</code>\n"
            f"Amount: <b>{sweep_amount:.2f} PRIZM</b>\n"
            f"Cold wallet: <code>{COLD_WALLET}</code>"
        )
    )
    return result


async def main() -> None:
    if not COLD_WALLET:
        log.warning(
            "[Sweep] PRIZM_COLD_WALLET env var is not set. Cold-storage sweep is DISABLED. All funds remain on hot wallet."
        )
    else:
        log.info(
            "[Sweep] Cold-storage sweep active. Threshold=%.0f PRIZM, MinKeep=%.0f PRIZM, ColdWallet=%s",
            SWEEP_THRESHOLD,
            SWEEP_MIN_KEEP,
            COLD_WALLET,
        )

    while True:
        try:
            await sweep_once()
        except Exception as exc:
            log.error("[Sweep] Unexpected error: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def get_runtime_status() -> dict[str, Any]:
    return {
        "cold_wallet_configured": bool(COLD_WALLET),
        "cold_wallet": COLD_WALLET,
        "sweep_threshold": SWEEP_THRESHOLD,
        "sweep_min_keep": SWEEP_MIN_KEEP,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
    }


if __name__ == "__main__":
    asyncio.run(main())
