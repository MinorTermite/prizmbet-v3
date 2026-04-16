#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRIZM Blockchain API — чтение транзакций кошелька"""

import json
import time
import requests

# Подтверждённые рабочие ноды (core.prizm.vip — основная, проверено 2026-02-28)
PRIZM_NODES = [
    "https://core.prizm.vip",
    "https://blockchain.prizm.vip",
]

import os
from backend.config import config as _cfg

# HOT wallet — used for all automatic operations (receiving bets, sending payouts).
# Address comes from PRIZM_HOT_WALLET env var; falls back to legacy PRIZM-4N7T address.
HOT_WALLET = _cfg.PRIZM_HOT_WALLET or "PRIZM-4N7T-L2A7-RQZA-5BETW"

# Legacy alias so existing code that imports `WALLET` keeps working unchanged.
WALLET = HOT_WALLET

# Passphrase: loaded lazily via get_hot_passphrase().
# Falls back to PRIZM_PASSPHRASE env var if no encrypted passphrase is stored in DB.
PASSPHRASE = os.getenv("PRIZM_PASSPHRASE", "")  # legacy fallback only

CACHE_FILE = os.path.join(os.path.dirname(__file__), "prizm_last_tx.json")
OUT_CACHE_FILE = os.path.join(os.path.dirname(__file__), "prizm_last_out_tx.json")
NQT = 100  # 1 PRIZM = 100 NQT


async def get_hot_passphrase() -> str:
    """Return the decrypted hot-wallet passphrase.

    Priority:
    1. Encrypted passphrase stored in DB (app_config.hot_wallet_passphrase_enc).
    2. Legacy PRIZM_PASSPHRASE env var (for existing deployments).
    Returns empty string if neither is set.
    """
    try:
        from backend.db.supabase_client import db as _db
        from backend.utils.wallet_crypto import decrypt_passphrase
        if _db.initialized:
            enc = await _db.get_app_config("hot_wallet_passphrase_enc")
            if enc:
                return decrypt_passphrase(enc)
    except Exception:
        pass
    return PASSPHRASE


def _get(params: dict, timeout=12) -> dict | None:
    for node in PRIZM_NODES:
        try:
            r = requests.get(f"{node}/prizm", params=params, timeout=timeout, verify=True)
            if r.ok:
                data = r.json()
                if "errorCode" not in data:
                    return data
        except Exception:
            continue
    return None


def _post(params: dict, timeout=12) -> dict | None:
    """Send a POST request to PRIZM nodes.  Use this for any call that
    includes sensitive data (e.g. secretPhrase) to keep it out of
    query strings / server access logs."""
    for node in PRIZM_NODES:
        try:
            r = requests.post(f"{node}/prizm", data=params, timeout=timeout, verify=True)
            if r.ok:
                data = r.json()
                if "errorCode" not in data:
                    return data
        except Exception:
            continue
    return None


def get_transactions(first_index=0, last_index=99, account=None) -> list[dict]:
    """Получить список транзакций кошелька PRIZM"""
    data = _get({
        "requestType": "getBlockchainTransactions",
        "account": account or WALLET,
        "type": 0,
        "firstIndex": first_index,
        "lastIndex": last_index,
    })
    if not data:
        return []
    return data.get("transactions", [])


def get_new_transactions() -> list[dict]:
    """Вернуть только новые транзакции (после последней проверки)"""
    last_ts = 0
    try:
        with open(CACHE_FILE) as f:
            last_ts = json.load(f).get("last_ts", 0)
    except Exception:
        pass

    txs = get_transactions()
    # Фильтруем только входящие на наш кошелёк (senderRS != WALLET)
    incoming = [t for t in txs if t.get("recipientRS") == WALLET or t.get("senderRS") != WALLET]
    new_txs = [t for t in incoming if t.get("timestamp", 0) > last_ts]

    if new_txs:
        new_last = max(t.get("timestamp", 0) for t in new_txs)
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"last_ts": new_last, "checked": int(time.time())}, f)
        except Exception:
            pass

    return new_txs


def decrypt_message(tx: dict, passphrase: str = "") -> str:
    """
    Расшифровать зашифрованное сообщение транзакции через PRIZM API readMessage.
    Использует POST чтобы secretPhrase не попадал в URL / access-логи.
    """
    secret = passphrase or PASSPHRASE
    if not secret:
        return ""
    tx_id = tx.get("transaction", "")
    if not tx_id:
        return ""
    data = _post({
        "requestType": "readMessage",
        "transaction": tx_id,
        "secretPhrase": secret,
    })
    if data:
        return data.get("decryptedMessage", data.get("message", "")).strip()
    return ""


def get_message(tx: dict) -> str:
    """
    Извлечь текстовое сообщение из транзакции.
    1. Сначала пробуем plain text (attachment.message)
    2. Если сообщение зашифровано и есть PASSPHRASE — расшифровываем через API
    """
    att = tx.get("attachment") or {}
    msg = att.get("message", "")
    is_text = att.get("messageIsText", True)
    if msg and is_text:
        return str(msg).strip()

    # Пробуем расшифровать
    if has_encrypted_message(tx):
        decrypted = decrypt_message(tx)
        if decrypted:
            return decrypted

    return ""


def has_encrypted_message(tx: dict) -> bool:
    """Проверить есть ли зашифрованное сообщение (ставка с шифрованием)"""
    att = tx.get("attachment") or {}
    return "encryptedMessage" in att


def get_new_outgoing_transactions() -> list[dict]:
    """Вернуть новые ИСХОДЯЩИЕ транзакции (отправленные с нашего кошелька)"""
    last_ts = 0
    try:
        with open(OUT_CACHE_FILE) as f:
            last_ts = json.load(f).get("last_ts", 0)
    except Exception:
        pass

    txs = get_transactions()
    outgoing = [t for t in txs if t.get("senderRS") == WALLET]
    new_txs = [t for t in outgoing if t.get("timestamp", 0) > last_ts]

    if new_txs:
        new_last = max(t.get("timestamp", 0) for t in new_txs)
        try:
            with open(OUT_CACHE_FILE, "w") as f:
                json.dump({"last_ts": new_last, "checked": int(time.time())}, f)
        except Exception:
            pass

    return new_txs


def parse_bet_comment(comment: str) -> dict | None:
    """
    Разобрать комментарий ставки.
    Формат: "27080379 П1 10" или "27080379 п2 5.5"
    Возвращает: {"match_id": "27080379", "bet_type": "П1", "amount": 10.0}
    """
    if not comment:
        return None
    parts = comment.strip().split()
    if len(parts) < 2:
        return None

    match_id = parts[0]
    if not match_id.isdigit():
        return None

    bet_type = parts[1].upper()
    valid_types = {"П1", "П2", "X", "1X", "X2", "12", "P1", "P2"}
    bet_type = bet_type.replace("P1", "П1").replace("P2", "П2")
    if bet_type not in valid_types:
        return None

    amount = 0.0
    if len(parts) >= 3:
        try:
            amount = float(parts[2].replace(",", "."))
        except ValueError:
            pass

    return {"match_id": match_id, "bet_type": bet_type, "amount": amount}


def prizm_amount(tx: dict) -> float:
    """Перевести внутренние единицы PRIZM → реальные монеты (1 PRIZM = 100,000,000 NQT)"""
    raw = tx.get("amountNQT", 0)
    try:
        return int(raw) / NQT
    except Exception:
        return 0.0


def get_coef(match: dict, outcome: str) -> float:
    """
    Получить коэффициент для исхода из данных матча.
    Поддерживает:
    1. Текущий плоский формат (p1, x, p2, p1x, p12, px2)
    2. Legacy формат (odds: {"1": ..., "X": ..., "2": ...})
    """
    if not match:
        return 0.0

    # Отображение исходов на плоские поля и ключи словаря odds
    flat_map = {"П1": "p1", "П2": "p2", "X": "x", "1X": "p1x", "X2": "px2", "12": "p12"}
    odds_map = {"П1": "1", "П2": "2", "X": "X", "1X": "1X", "X2": "X2", "12": "12"}

    # 1. Пробуем плоский формат
    field = flat_map.get(outcome)
    if field and field in match:
        val = match.get(field)
        if val and val not in ("—", "-", "0.00", ""):
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

    # 2. Пробуем вложенный словарь odds (legacy)
    odds = match.get("odds") or {}
    key = odds_map.get(outcome, outcome)
    val = odds.get(key)
    if val and val not in ("—", "-", "0.00", ""):
        try:
            return float(val)
        except (ValueError, TypeError):
            pass

    return 0.0


def get_sender_address(tx: dict) -> str:
    return tx.get("senderRS", tx.get("sender", "unknown"))


async def send_money(recipient: str, amount: float, message: str = "") -> dict | None:
    """Send PRIZM via the blockchain sendMoney API.

    Returns the parsed JSON response on success (contains 'transaction' key),
    or None on failure.
    """
    passphrase = await get_hot_passphrase()
    if not passphrase:
        return None

    amount_nqt = int(round(amount * NQT))
    if amount_nqt <= 0:
        return None

    params = {
        "requestType": "sendMoney",
        "secretPhrase": passphrase,
        "recipient": recipient,
        "amountNQT": str(amount_nqt),
        "feeNQT": "5",
        "deadline": "1440",
    }
    if message:
        params["message"] = message
        params["messageIsText"] = "true"

    for node in PRIZM_NODES:
        try:
            resp = requests.post(f"{node}/prizm", data=params, timeout=20, verify=True)
            if not resp.ok:
                continue
            data = resp.json()
            if "errorCode" in data:
                continue
            if data.get("transaction"):
                return data
        except Exception:
            continue
    return None


def get_balance() -> dict:
    """
    Получить баланс кошелька PRIZM.
    Возвращает: {"balance": float, "unconfirmed": float, "wallet": str, "node": str}
    """
    for node in PRIZM_NODES:
        try:
            r = requests.get(
                f"{node}/prizm",
                params={"requestType": "getAccount", "account": WALLET},
                timeout=12,
                verify=True,
            )
            if not r.ok:
                continue
            data = r.json()
            if "errorCode" in data:
                continue
            balance_nqt     = int(data.get("balanceNQT", 0))
            unconfirmed_nqt = int(data.get("unconfirmedBalanceNQT", 0))
            return {
                "balance":     balance_nqt / NQT,
                "unconfirmed": unconfirmed_nqt / NQT,
                "wallet":      WALLET,
                "node":        node,
            }
        except Exception:
            continue
    return {"balance": None, "unconfirmed": None, "wallet": WALLET, "node": None}
