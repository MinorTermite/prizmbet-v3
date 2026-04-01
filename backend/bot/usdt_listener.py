#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USDT TRC-20 Transaction Listener.

Polls TronGrid for incoming USDT transfers to USDT_HOT_WALLET.
Matches transfers to bet intents by sender address (wallet fallback only —
TRON TRC-20 transfers have no message field).

The listener stores its checkpoint as usdt_last_block_ts in tx_listener_state.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from backend.config import config
from backend.db.supabase_client import db
from backend.bot import usdt_api
from backend.utils.operator_audit import log_operator_event
from backend.utils.operator_alerts import notify_bet_processed

POLL_INTERVAL_SECONDS = 30
SAFETY_WINDOW_SECONDS = 120

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


async def _ensure_db():
    if not db.initialized:
        db.init()
    if not db.initialized:
        raise RuntimeError("Supabase is not configured")


async def _get_checkpoint() -> int:
    """Get last processed TRON block_timestamp (milliseconds)."""
    state = await db.get_listener_state()
    if not state:
        return 0
    return int(state.get("usdt_last_block_ts", 0) or 0)


async def _update_checkpoint(block_ts_ms: int):
    """Save USDT listener checkpoint alongside PRIZM state."""
    await db.upsert_listener_state(usdt_last_block_ts=block_ts_ms)


async def _resolve_wallet_intent(sender_wallet: str, block_ts_utc: datetime):
    """Find a matching intent by sender wallet address."""
    intents = await db.get_active_wallet_intents(sender_wallet, block_ts_utc.isoformat())
    if not intents:
        return None, "INVALID_INTENT"

    existing_bets = await db.get_bets_by_intent_hashes(
        [str(item.get("intent_hash") or "") for item in intents]
    )
    taken = {
        str(item.get("intent_hash") or "").strip().upper()
        for item in existing_bets
        if item.get("intent_hash")
    }
    available = [
        item
        for item in intents
        if str(item.get("intent_hash") or "").strip().upper() not in taken
    ]

    if len(available) == 1:
        return available[0], None
    if len(available) > 1:
        return None, "AMBIGUOUS_WALLET_INTENT"
    return None, "INVALID_INTENT"


async def _process_transfer(transfer: dict):
    """Process a single incoming USDT TRC-20 transfer."""
    parsed = usdt_api.parse_transfer(transfer)
    tx_id = parsed["tx_id"]
    if not tx_id:
        return

    amount = parsed["amount_usdt"]
    sender = parsed["from_address"]
    block_ts_ms = parsed["block_timestamp_ms"]
    block_ts_utc = datetime.fromtimestamp(block_ts_ms / 1000, tz=timezone.utc)

    bet_row = {
        "tx_id": f"usdt_{tx_id}",
        "intent_hash": None,
        "match_id": "unknown",
        "sender_wallet": sender,
        "amount_prizm": amount,  # Column reused; actual currency tracked via payment_currency
        "payment_currency": "USDT",
        "odds_fixed": 1.00,
        "status": "rejected",
        "reject_reason": "INVALID_INTENT",
        "block_timestamp": block_ts_utc.isoformat(),
    }

    intent = None
    match = None

    # TRC-20 transfers have no message — resolve by wallet only
    intent, fallback_reason = await _resolve_wallet_intent(sender, block_ts_utc)
    if intent:
        intent_hash = str(intent.get("intent_hash") or "").strip().upper()
        bet_row["intent_hash"] = intent_hash
    else:
        bet_row["reject_reason"] = fallback_reason or "INVALID_INTENT"

    if not intent:
        pass  # reject_reason already set
    elif amount > config.USDT_MAX_BET:
        bet_row["match_id"] = str(intent["match_id"])
        bet_row["odds_fixed"] = float(intent["odds_fixed"])
        bet_row["reject_reason"] = "MAX_BET_EXCEEDED"
    elif amount < config.USDT_MIN_BET:
        bet_row["match_id"] = str(intent["match_id"])
        bet_row["odds_fixed"] = float(intent["odds_fixed"])
        bet_row["reject_reason"] = "DUST_DONATION"
    else:
        match = await db.get_match_by_id(str(intent["match_id"]))
        expires_at = datetime.fromisoformat(
            str(intent["expires_at"]).replace("Z", "+00:00")
        )
        bet_row.update({
            "match_id": str(intent["match_id"]),
            "odds_fixed": float(intent["odds_fixed"]),
        })

        if sender.upper() != str(intent["sender_wallet"]).upper():
            bet_row["reject_reason"] = "SENDER_MISMATCH"
        elif block_ts_utc > expires_at:
            bet_row["reject_reason"] = "INTENT_EXPIRED"
        elif not match:
            bet_row["reject_reason"] = "MATCH_NOT_FOUND"
        elif bool(match.get("is_live")):
            bet_row["reject_reason"] = "LIVE_DISABLED"
        else:
            match_time = datetime.fromisoformat(
                str(match["match_time"]).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            cutoff = match_time - timedelta(seconds=SAFETY_WINDOW_SECONDS)
            if block_ts_utc > cutoff:
                bet_row["reject_reason"] = "LATE_BET"
            else:
                bet_row["status"] = "accepted"
                bet_row["reject_reason"] = None

    try:
        await db.insert_bet(bet_row)
        if bet_row["status"] == "accepted":
            log.info("[USDT ACCEPTED] Tx %s amount=%.2f", tx_id[:16], amount)
        else:
            log.info("[USDT REJECTED] Tx %s Reason: %s", tx_id[:16], bet_row["reject_reason"])

        await log_operator_event(
            "usdt_bet_accepted" if bet_row["status"] == "accepted" else "usdt_bet_rejected",
            dict(bet_row),
            intent=dict(intent) if intent else None,
            match=dict(match) if match else None,
            reason=bet_row.get("reject_reason"),
            extra={"currency": "USDT"},
        )

        asyncio.create_task(
            notify_bet_processed(
                dict(bet_row),
                intent=dict(intent) if intent else None,
                match=dict(match) if match else None,
            )
        )
    except Exception as e:
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            return
        raise


async def run_once():
    """One poll cycle: fetch new USDT transfers and process them."""
    await _ensure_db()
    last_ts = await _get_checkpoint()

    transfers = await usdt_api.get_trc20_transfers(
        min_timestamp=last_ts + 1 if last_ts else 0,
        limit=50,
    )

    if not transfers:
        return

    max_ts = last_ts
    for tx in transfers:
        block_ts = int(tx.get("block_timestamp", 0))
        tx_id = tx.get("transaction_id", "")
        await _process_transfer(tx)
        if block_ts > max_ts:
            max_ts = block_ts

    if max_ts > last_ts:
        await _update_checkpoint(max_ts)


async def main():
    if not config.USDT_ENABLED:
        log.info("USDT listener disabled (USDT_ENABLED != true)")
        # Sleep forever so the task doesn't crash the service runner
        while True:
            await asyncio.sleep(3600)

    if not config.USDT_HOT_WALLET:
        log.warning("USDT_HOT_WALLET not set — USDT listener will not start")
        while True:
            await asyncio.sleep(3600)

    log.info("Starting USDT Tx Listener for wallet %s", config.USDT_HOT_WALLET)
    while True:
        try:
            await run_once()
        except Exception as e:
            log.error("USDT listener loop error: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
