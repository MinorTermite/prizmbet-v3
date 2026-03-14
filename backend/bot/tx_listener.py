#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRIZM Tx Listener + Anti-fraud."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from backend.config import config
from backend.db.supabase_client import db
from backend.bot import prizm_api
from backend.utils.operator_alerts import notify_bet_processed
WALLET = prizm_api.WALLET
SAFETY_WINDOW_SECONDS = 120
POLL_INTERVAL_SECONDS = 30
PAGE_SIZE = 100

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def _to_utc_from_prizm(ts: int) -> datetime:
    # PRIZM timestamp = seconds since PRIZM/NXT epoch
    return datetime.fromtimestamp(config.PRIZM_EPOCH + int(ts), tz=timezone.utc)


def _extract_intent_hash(comment: str) -> str:
    text = (comment or "").strip().upper()
    if 1 <= len(text) <= 12 and text.isalnum():
        return text
    return ""


async def _ensure_db():
    if not db.initialized:
        db.init()
    if not db.initialized:
        raise RuntimeError("Supabase is not configured")


async def _get_checkpoint():
    state = await db.get_listener_state()
    if not state:
        return 0, ""
    return int(state.get("last_prizm_timestamp", 0)), state.get("last_tx_id") or ""


async def _update_checkpoint(ts: int, tx_id: str):
    await db.upsert_listener_state(last_prizm_timestamp=ts, last_tx_id=tx_id)


async def _process_tx(tx: dict):
    tx_id = tx.get("transaction", "")
    if not tx_id:
        return
    if tx.get("senderRS") == WALLET:
        return
    if tx.get("recipientRS") != WALLET:
        return

    amount = round(prizm_api.prizm_amount(tx), 2)
    block_ts_native = int(tx.get("timestamp", 0) or 0)
    block_ts_utc = _to_utc_from_prizm(block_ts_native)
    sender_wallet = (tx.get("senderRS") or "").upper()

    comment = prizm_api.get_message(tx)
    intent_hash = _extract_intent_hash(comment)

    bet_row = {
        "tx_id": tx_id,
        "intent_hash": intent_hash or None,
        "match_id": "unknown",
        "sender_wallet": sender_wallet,
        "amount_prizm": amount,
        "odds_fixed": 1.00,
        "status": "rejected",
        "reject_reason": "INVALID_INTENT",
        "block_timestamp": block_ts_utc.isoformat(),
    }

    intent = None
    match = None
    if intent_hash:
        intent = await db.get_bet_intent(intent_hash)

    if not intent:
        bet_row["reject_reason"] = "INVALID_INTENT"
    elif amount < config.MIN_BET:
        bet_row["match_id"] = str(intent["match_id"])
        bet_row["odds_fixed"] = float(intent["odds_fixed"])
        bet_row["reject_reason"] = "DUST_DONATION"
    else:
        match = await db.get_match_by_id(str(intent["match_id"]))
        expires_at = datetime.fromisoformat(str(intent["expires_at"]).replace("Z", "+00:00"))
        bet_row.update({
            "match_id": str(intent["match_id"]),
            "odds_fixed": float(intent["odds_fixed"]),
        })

        if sender_wallet != str(intent["sender_wallet"]).upper():
            bet_row["reject_reason"] = "SENDER_MISMATCH"
        elif block_ts_utc > expires_at:
            bet_row["reject_reason"] = "INTENT_EXPIRED"
        elif not match:
            bet_row["reject_reason"] = "MATCH_NOT_FOUND"
        elif bool(match.get("is_live")):
            bet_row["reject_reason"] = "LIVE_DISABLED"
        else:
            match_time = datetime.fromisoformat(str(match["match_time"]).replace("Z", "+00:00")).astimezone(timezone.utc)
            cutoff = match_time - timedelta(seconds=SAFETY_WINDOW_SECONDS)
            if block_ts_utc > cutoff:
                bet_row["reject_reason"] = "LATE_BET"
            else:
                bet_row["status"] = "accepted"
                bet_row["reject_reason"] = None

    try:
        await db.insert_bet(bet_row)
        if bet_row["status"] == "accepted":
            log.info("[ACCEPTED] Tx %s amount=%.2f intent=%s", tx_id[:16], amount, intent_hash)
        else:
            log.info("[REJECTED] Tx %s Reason: %s", tx_id[:16], bet_row["reject_reason"])

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
    await _ensure_db()
    last_ts, last_tx = await _get_checkpoint()

    txs = []
    first_index = 0
    while True:
        page = prizm_api.get_transactions(
            first_index=first_index,
            last_index=first_index + PAGE_SIZE - 1,
        )
        if not page:
            break

        txs.extend(page)

        if len(page) < PAGE_SIZE:
            break

        if all(int(tx.get("timestamp", 0) or 0) < last_ts for tx in page):
            break

        first_index += PAGE_SIZE

    unique_txs = {}
    for tx in txs:
        tx_id = tx.get("transaction", "")
        if tx_id:
            unique_txs[tx_id] = tx

    txs = sorted(
        unique_txs.values(),
        key=lambda x: (int(x.get("timestamp", 0) or 0), x.get("transaction", "")),
    )

    for tx in txs:
        ts = int(tx.get("timestamp", 0) or 0)
        tx_id = tx.get("transaction", "")
        if ts < last_ts:
            continue
        if ts == last_ts and last_tx and tx_id <= last_tx:
            continue
        await _process_tx(tx)
        await _update_checkpoint(ts, tx_id)


async def main():
    log.info("Starting Tx Listener for wallet %s", WALLET)
    while True:
        try:
            await run_once()
        except Exception as e:
            log.error("Tx listener loop error: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
