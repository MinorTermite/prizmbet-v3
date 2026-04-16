#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cold-storage sweep: automatically transfers excess PRIZM from the hot wallet
to the cold (reserve) wallet when the balance exceeds SWEEP_THRESHOLD.

Configuration (env vars):
  PRIZM_COLD_WALLET  — destination cold wallet address (required to enable sweep)
  PRIZM_SWEEP_THRESHOLD — trigger balance in PRIZM (default: 300000)
  PRIZM_SWEEP_MIN_KEEP  — minimum PRIZM to keep on hot wallet after sweep (default: 50000)

The sweep runs every POLL_INTERVAL_SECONDS (default: 600 — every 10 minutes).
If PRIZM_COLD_WALLET is not set, the loop logs a warning and remains idle.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from backend.bot import prizm_api
from backend.db.supabase_client import db
from backend.utils.telegram_v3 import telegram_v3

POLL_INTERVAL_SECONDS = 600          # check every 10 minutes
SWEEP_THRESHOLD  = float(os.getenv("PRIZM_SWEEP_THRESHOLD",  "300000"))
SWEEP_MIN_KEEP   = float(os.getenv("PRIZM_SWEEP_MIN_KEEP",    "50000"))
COLD_WALLET      = os.getenv("PRIZM_COLD_WALLET", "").strip()

log = logging.getLogger(__name__)


async def _notify(msg: str) -> None:
    """Send Telegram alert if configured."""
    try:
        if telegram_v3.enabled:
            await telegram_v3.send_message_many(msg, parse_mode="HTML")
    except Exception as exc:
        log.warning("Telegram notify failed: %s", exc)


async def sweep_once() -> dict[str, Any] | None:
    """
    Performs a single sweep check.
    Returns the sendMoney result dict if a sweep was executed, else None.
    """
    if not COLD_WALLET:
        log.debug("[Sweep] PRIZM_COLD_WALLET not set — sweep disabled")
        return None

    info = prizm_api.get_balance()
    balance = info.get("balance")
    if balance is None:
        log.warning("[Sweep] Could not fetch hot-wallet balance")
        return None

    log.debug("[Sweep] Hot wallet balance: %.2f PRIZM (threshold: %.0f)", balance, SWEEP_THRESHOLD)

    if balance <= SWEEP_THRESHOLD:
        return None

    sweep_amount = round(balance - SWEEP_MIN_KEEP, 2)
    if sweep_amount <= 0:
        log.warning("[Sweep] Computed sweep amount is zero — skip")
        return None

    log.info(
        "[Sweep] Balance %.2f > %.0f threshold → sweeping %.2f PRIZM to cold wallet %s",
        balance, SWEEP_THRESHOLD, sweep_amount, COLD_WALLET,
    )

    await _notify(
        f"<b>Cold Storage Sweep</b>\n"
        f"Hot balance: <b>{balance:.2f} PRIZM</b>\n"
        f"Sweeping: <b>{sweep_amount:.2f} PRIZM</b>\n"
        f"To cold: <code>{COLD_WALLET}</code>"
    )

    result = await prizm_api.send_money(
        recipient=COLD_WALLET,
        amount=sweep_amount,
        message="PrizmBet cold-storage sweep",
    )

    if result and result.get("transaction"):
        tx_id = result["transaction"]
        log.info("[Sweep] SUCCESS tx=%s amount=%.2f PRIZM swept to %s", tx_id, sweep_amount, COLD_WALLET)

        await _notify(
            f"<b>Sweep Completed</b>\n"
            f"TX: <code>{tx_id}</code>\n"
            f"Amount: <b>{sweep_amount:.2f} PRIZM</b>\n"
            f"Cold wallet: <code>{COLD_WALLET}</code>"
        )

        # Write to ledger
        try:
            await db.insert_ledger_entry({
                "tx_type": "sweep",
                "prizm_tx_id": tx_id,
                "wallet": COLD_WALLET,
                "amount_prizm": sweep_amount,
                "fee_prizm": 0.05,
                "note": "cold-storage sweep",
            })
        except Exception as exc:
            log.warning("[Sweep] Ledger write failed: %s", exc)
    else:
        log.error("[Sweep] FAILED to sweep %.2f PRIZM to %s", sweep_amount, COLD_WALLET)
        await _notify(
            f"<b>Sweep FAILED</b>\n"
            f"Amount: {sweep_amount:.2f} PRIZM\n"
            f"Cold: <code>{COLD_WALLET}</code>\n"
            f"Check logs!"
        )

    return result


async def main() -> None:
    if not COLD_WALLET:
        log.warning(
            "[Sweep] PRIZM_COLD_WALLET env var is not set. "
            "Cold-storage sweep is DISABLED. All funds remain on hot wallet."
        )
    else:
        log.info(
            "[Sweep] Cold-storage sweep active. Threshold=%.0f PRIZM, "
            "MinKeep=%.0f PRIZM, ColdWallet=%s",
            SWEEP_THRESHOLD, SWEEP_MIN_KEEP, COLD_WALLET,
        )

    while True:
        try:
            await sweep_once()
        except Exception as exc:
            log.error("[Sweep] Unexpected error: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
