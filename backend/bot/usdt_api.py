#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USDT TRC-20 (TRON) API helpers — balance, transfer history, send."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from backend.config import config

log = logging.getLogger(__name__)

USDT_DECIMALS = 6  # USDT has 6 decimals on TRON
WALLET = config.USDT_HOT_WALLET
CONTRACT = config.USDT_CONTRACT
API_URL = config.TRON_API_URL


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    if config.TRON_API_KEY:
        h["TRON-PRO-API-KEY"] = config.TRON_API_KEY
    return h


def usdt_amount(raw_value: str | int) -> float:
    """Convert raw USDT integer value (6 decimals) to float."""
    try:
        return int(raw_value) / (10 ** USDT_DECIMALS)
    except (TypeError, ValueError):
        return 0.0


async def get_balance(wallet: str | None = None) -> float:
    """Get USDT TRC-20 balance for a wallet address."""
    addr = wallet or WALLET
    if not addr:
        return 0.0
    url = f"{API_URL}/v1/accounts/{addr}/tokens"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=_headers(), timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    log.warning("TronGrid balance %s: %s", addr[:10], r.status)
                    return 0.0
                data = await r.json()
                for token in data.get("data", []):
                    if token.get("tokenId") == CONTRACT or token.get("tokenAbbr") == "USDT":
                        return usdt_amount(token.get("balance", 0))
    except Exception as e:
        log.error("USDT balance error: %s", e)
    return 0.0


async def get_trc20_transfers(
    wallet: str | None = None,
    min_timestamp: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Fetch incoming USDT TRC-20 transfers to the wallet.

    Uses TronGrid /v1/accounts/{address}/transactions/trc20 endpoint.
    Returns list of transfer dicts sorted by block_timestamp ascending.
    """
    addr = wallet or WALLET
    if not addr:
        return []

    url = f"{API_URL}/v1/accounts/{addr}/transactions/trc20"
    params: dict[str, Any] = {
        "only_to": "true",
        "only_confirmed": "true",
        "contract_address": CONTRACT,
        "limit": limit,
        "order_by": "block_timestamp,asc",
    }
    if min_timestamp > 0:
        params["min_timestamp"] = min_timestamp

    all_transfers: list[dict[str, Any]] = []
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, headers=_headers(),
                             timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    log.warning("TronGrid trc20 transfers %s: %s", addr[:10], r.status)
                    return []
                data = await r.json()
                all_transfers = data.get("data", [])
    except Exception as e:
        log.error("USDT transfers error: %s", e)

    return all_transfers


def parse_transfer(tx: dict[str, Any]) -> dict[str, Any]:
    """Normalize a TronGrid TRC-20 transfer to a flat dict."""
    return {
        "tx_id": tx.get("transaction_id", ""),
        "from_address": tx.get("from", ""),
        "to_address": tx.get("to", ""),
        "amount_usdt": usdt_amount(tx.get("value", 0)),
        "block_timestamp_ms": int(tx.get("block_timestamp", 0)),
        "token_symbol": tx.get("token_info", {}).get("symbol", "USDT"),
    }
