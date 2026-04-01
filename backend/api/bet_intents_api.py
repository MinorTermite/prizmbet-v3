# -*- coding: utf-8 -*-
"""Bet Intent API for public v3 flow and operator auth."""
from __future__ import annotations

import collections
import csv
import io
import json
import os
import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aiohttp import web

from backend.config import config
from backend.db.supabase_client import db
from backend.utils.admin_auth import (
    client_ip,
    hash_password,
    issue_session_token,
    normalize_email,
    normalize_login,
    normalize_role,
    role_can_manage_users,
    role_can_mark_paid,
    serialize_admin_user,
    session_expires_at,
    session_token_hash,
    validate_email,
    validate_login,
    validate_password,
    verify_password,
)
from backend.utils.bet_views import ACCEPTED_STATUSES, build_bet_view, search_blob
from backend.utils.operator_alerts import notify_payout_sent
from backend.utils.operator_audit import log_operator_event, mirror_operator_event


OUTCOME_MAP = {
    "P1": "p1",
    "1": "p1",
    "X": "x",
    "P2": "p2",
    "2": "p2",
    "1X": "p1x",
    "12": "p12",
    "X2": "px2",
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key, X-Admin-Session, Authorization",
}

MATCHES_CACHE_PATH = Path(__file__).resolve().parents[2] / "frontend" / "matches.json"


def _with_cors(response: web.StreamResponse) -> web.StreamResponse:
    response.headers.update(CORS_HEADERS)
    return response


def _json_response(payload: dict[str, Any], status: int = 200) -> web.Response:
    return _with_cors(web.json_response(payload, status=status))


def _load_matches_cache() -> dict[str, dict[str, Any]]:
    if not MATCHES_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(MATCHES_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(match.get("id")): match for match in data.get("matches", []) if match.get("id")}


def _extract_odds(match: dict[str, Any], outcome: str) -> float | None:
    key = OUTCOME_MAP.get(str(outcome or "").strip().upper())
    if not key:
        return None
    value = match.get(key)
    if not value or value in ("-", "—", "0", "0.00"):
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _intent_hash(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _rank_preview(turnover: float, accepted_count: int) -> dict[str, Any]:
    tiers = [
        ("Beginner", 0),
        ("Player", 1500),
        ("Regular", 5000),
        ("Pro", 15000),
        ("Master", 50000),
    ]
    current = tiers[0]
    next_tier = None
    for tier in tiers:
        if turnover >= tier[1]:
            current = tier
        elif next_tier is None:
            next_tier = tier
            break

    if next_tier is None:
        progress = 100
    else:
        span = max(next_tier[1] - current[1], 1)
        progress = int(min(100, max(0, ((turnover - current[1]) / span) * 100)))

    return {
        "current": current[0],
        "accepted_count": accepted_count,
        "turnover_prizm": round(turnover, 2),
        "next": None if next_tier is None else {
            "name": next_tier[0],
            "target_turnover": next_tier[1],
            "remaining_prizm": round(max(next_tier[1] - turnover, 0), 2),
        },
        "progress_percent": progress,
    }


async def _find_wallet_pending_intent(sender_wallet: str, now_utc: datetime) -> tuple[str, dict[str, Any] | None]:
    intents = await db.get_active_wallet_intents(sender_wallet, now_utc.isoformat())
    if not intents:
        return 'none', None

    bets = await db.get_bets_by_intent_hashes([str(item.get('intent_hash') or '') for item in intents])
    taken = {str(row.get('intent_hash') or '').strip().upper() for row in bets if row.get('intent_hash')}
    pending = [item for item in intents if str(item.get('intent_hash') or '').strip().upper() not in taken]

    if len(pending) == 1:
        return 'single', pending[0]
    if len(pending) > 1:
        return 'multiple', None
    return 'none', None


def _bootstrap_key_valid(request: web.Request, payload: dict[str, Any] | None = None) -> bool:
    required_key = str(config.ADMIN_VIEW_KEY or "").strip()
    if not required_key:
        return False
    payload = payload or {}
    provided = str(
        request.headers.get("X-Admin-Key")
        or request.query.get("admin_key")
        or payload.get("bootstrap_key")
        or ""
    ).strip()
    return bool(provided) and secrets.compare_digest(provided, required_key)


def _extract_session_token(request: web.Request) -> str:
    header_token = str(request.headers.get("X-Admin-Session") or "").strip()
    if header_token:
        return header_token
    auth_header = str(request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return str(request.query.get("session_token") or "").strip()


def _mask_email(email: str) -> str:
    email = normalize_email(email)
    if "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(len(local) - 2, 1)
    return f"{masked_local}@{domain}"


def _actor_from_user(user: dict[str, Any] | None, auth_mode: str = "session") -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "id": user.get("id"),
        "login": user.get("login"),
        "role": user.get("role"),
        "auth_mode": auth_mode,
    }


def _is_operator_noise(view: dict[str, Any]) -> bool:
    status = str(view.get("status") or "").strip().lower()
    reject_reason = str(view.get("reject_reason") or "").strip().upper()
    match_id = str(view.get("match_id") or "").strip().lower()
    intent_hash = str(view.get("intent_hash") or "").strip()
    amount = float(view.get("amount_prizm") or 0)
    ts = _parse_dt(view.get("block_timestamp"))
    stale_timestamp = bool(ts and ts.astimezone(timezone.utc).year < 2025)
    return (
        status == "rejected"
        and reject_reason in {"INVALID_INTENT", "DUST_DONATION"}
        and match_id in {"", "unknown"}
        and not intent_hash
        and (stale_timestamp or amount < float(config.MIN_BET))
    )


async def _log_admin_access_event(event_type: str, *, actor: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "event_type": event_type,
        "status": "admin",
        "actor": actor or {},
        "extra": extra or {},
        "created_at": timestamp,
    }
    audit_row = {
        "event_type": event_type,
        "tx_id": None,
        "intent_hash": None,
        "match_id": None,
        "status": "admin",
        "sender_wallet": None,
        "amount_prizm": 0,
        "payload": payload,
        "created_at": timestamp,
    }
    await db.insert_operator_audit_log(audit_row)
    await mirror_operator_event(payload)


async def _ensure_db_ready() -> bool:
    if not db.initialized:
        db.init()
    return db.initialized


async def _create_session_for_user(user: dict[str, Any], request: web.Request) -> dict[str, Any]:
    token = issue_session_token()
    token_hash = session_token_hash(token)
    expires_at = session_expires_at()
    session_row = {
        "token_hash": token_hash,
        "admin_user_id": user.get("id"),
        "expires_at": expires_at,
        "user_agent": str(request.headers.get("User-Agent") or "")[:500],
        "ip": client_ip(request)[:120],
    }
    await db.insert_admin_session(session_row)
    return {
        "token": token,
        "expires_at": expires_at,
    }


async def _get_admin_context(request: web.Request) -> tuple[dict[str, Any] | None, web.Response | None]:
    if not await _ensure_db_ready():
        return None, _json_response({"error": "Database not configured"}, status=500)

    token = _extract_session_token(request)
    if not token:
        return None, _json_response({"error": "Admin session is required"}, status=401)

    await db.delete_expired_admin_sessions()
    token_hash = session_token_hash(token)
    session = await db.get_admin_session(token_hash)
    if not session:
        return None, _json_response({"error": "Admin session is invalid or expired"}, status=401)

    expires_at = _parse_dt(session.get("expires_at"))
    now = datetime.now(timezone.utc)
    if expires_at and expires_at.astimezone(timezone.utc) <= now:
        await db.delete_admin_session(token_hash)
        return None, _json_response({"error": "Admin session is invalid or expired"}, status=401)

    user = await db.get_admin_user_by_id(session.get("admin_user_id"))
    if not user:
        await db.delete_admin_session(token_hash)
        return None, _json_response({"error": "Admin user not found"}, status=401)
    if not bool(user.get("is_active", True)):
        await db.delete_admin_session(token_hash)
        return None, _json_response({"error": "Admin user is disabled"}, status=403)

    await db.touch_admin_session(token_hash)
    return {
        "user": user,
        "session": session,
        "session_token": token,
        "actor": _actor_from_user(user, "session"),
    }, None


async def _require_admin(request: web.Request, roles: set[str] | None = None) -> tuple[dict[str, Any] | None, web.Response | None]:
    context, error = await _get_admin_context(request)
    if error:
        return None, error
    role = str(context["user"].get("role") or "").strip().lower()
    if roles and role not in roles:
        return None, _json_response({"error": "Insufficient permissions"}, status=403)
    return context, None


async def bootstrap_state(_: web.Request) -> web.Response:
    db_ready = await _ensure_db_ready()
    has_users = await db.has_admin_users() if db_ready else False
    bootstrap_allowed = bool(db_ready and not has_users and str(config.ADMIN_VIEW_KEY or "").strip())
    result = {
        "db_configured": db_ready,
        "has_admin_users": has_users,
        "bootstrap_allowed": bootstrap_allowed,
        "bootstrap_key_configured": bool(str(config.ADMIN_VIEW_KEY or "").strip()),
    }
    # Only expose owner hints during bootstrap (before first admin is created)
    if bootstrap_allowed:
        result["owner_login"] = config.SUPER_ADMIN_LOGIN
        result["owner_email_hint"] = _mask_email(config.SUPER_ADMIN_EMAIL)
    return _json_response(result)


async def bootstrap_admin(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)
    if await db.has_admin_users():
        return _json_response({"error": "Bootstrap is already completed"}, status=409)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    if not _bootstrap_key_valid(request, payload):
        return _json_response({"error": "Bootstrap key is invalid or missing"}, status=401)

    email = normalize_email(payload.get("email"))
    login = normalize_login(payload.get("login"))
    password = str(payload.get("password") or "")

    if not validate_email(email):
        return _json_response({"error": "A valid owner email is required"}, status=400)
    if not validate_login(login):
        return _json_response({"error": "Owner login must be 3-32 lowercase latin characters"}, status=400)
    if not validate_password(password):
        return _json_response({"error": "Password must contain at least 8 characters"}, status=400)
    if email != config.SUPER_ADMIN_EMAIL or login != config.SUPER_ADMIN_LOGIN:
        return _json_response({"error": "Bootstrap is restricted to the configured owner identity"}, status=403)

    user = await db.create_admin_user({
        "login": login,
        "email": email,
        "password_hash": hash_password(password),
        "role": "super_admin",
        "is_active": True,
        "last_login_at": datetime.now(timezone.utc).isoformat(),
    })
    if not user:
        return _json_response({"error": "Failed to create the owner account"}, status=500)

    session = await _create_session_for_user(user, request)
    await _log_admin_access_event(
        "admin_bootstrap_completed",
        actor=_actor_from_user(user, "bootstrap"),
        extra={"owner_email": email, "owner_login": login},
    )
    return _json_response({"ok": True, "user": serialize_admin_user(user), "session": session})


async def admin_login(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)
    if not await db.has_admin_users():
        return _json_response({"error": "Bootstrap is required before login"}, status=409)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    identity = str(payload.get("identity") or "").strip()
    password = str(payload.get("password") or "")
    if not identity or not password:
        return _json_response({"error": "identity and password are required"}, status=400)

    user = await db.get_admin_user_by_login(normalize_login(identity))
    if not user and "@" in identity:
        user = await db.get_admin_user_by_email(normalize_email(identity))
    if not user:
        return _json_response({"error": "Invalid credentials"}, status=401)
    if not bool(user.get("is_active", True)):
        return _json_response({"error": "Admin user is disabled"}, status=403)
    if not verify_password(password, str(user.get("password_hash") or "")):
        return _json_response({"error": "Invalid credentials"}, status=401)

    await db.delete_expired_admin_sessions()
    await db.update_admin_user(user.get("id"), {"last_login_at": datetime.now(timezone.utc).isoformat()})
    user = await db.get_admin_user_by_id(user.get("id")) or user
    session = await _create_session_for_user(user, request)
    await _log_admin_access_event(
        "admin_login",
        actor=_actor_from_user(user, "session"),
        extra={"ip": client_ip(request)},
    )
    return _json_response({"ok": True, "user": serialize_admin_user(user), "session": session})


async def admin_logout(request: web.Request) -> web.Response:
    context, error = await _require_admin(request)
    if error:
        return error

    await db.delete_admin_session(session_token_hash(context["session_token"]))
    await _log_admin_access_event(
        "admin_logout",
        actor=context["actor"],
        extra={"ip": client_ip(request)},
    )
    return _json_response({"ok": True})


async def admin_me(request: web.Request) -> web.Response:
    context, error = await _require_admin(request)
    if error:
        return error
    return _json_response({
        "ok": True,
        "user": serialize_admin_user(context["user"]),
        "session": {
            "expires_at": context["session"].get("expires_at"),
            "last_seen_at": context["session"].get("last_seen_at"),
        },
    })

async def admin_users(request: web.Request) -> web.Response:
    context, error = await _require_admin(request, {"super_admin"})
    if error:
        return error
    users = await db.list_admin_users()
    return _json_response({
        "ok": True,
        "users": [serialize_admin_user(user) for user in users],
        "current_user_id": context["user"].get("id"),
    })


async def admin_create_user(request: web.Request) -> web.Response:
    context, error = await _require_admin(request, {"super_admin"})
    if error:
        return error

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    login = normalize_login(payload.get("login"))
    email = normalize_email(payload.get("email"))
    password = str(payload.get("password") or "")
    role = normalize_role(payload.get("role"), allow_super_admin=False)

    if not validate_login(login):
        return _json_response({"error": "Login must be 3-32 lowercase latin characters"}, status=400)
    if email and not validate_email(email):
        return _json_response({"error": "Email format is invalid"}, status=400)
    if not validate_password(password):
        return _json_response({"error": "Password must contain at least 8 characters"}, status=400)
    if await db.get_admin_user_by_login(login):
        return _json_response({"error": "Login is already used"}, status=409)
    if email and await db.get_admin_user_by_email(email):
        return _json_response({"error": "Email is already used"}, status=409)

    user = await db.create_admin_user({
        "login": login,
        "email": email or None,
        "password_hash": hash_password(password),
        "role": role,
        "is_active": True,
    })
    if not user:
        return _json_response({"error": "Failed to create admin user"}, status=500)

    await _log_admin_access_event(
        "admin_user_created",
        actor=context["actor"],
        extra={"target_user_id": user.get("id"), "target_login": login, "target_role": role},
    )
    return _json_response({"ok": True, "user": serialize_admin_user(user)})


async def admin_set_user_active(request: web.Request) -> web.Response:
    context, error = await _require_admin(request, {"super_admin"})
    if error:
        return error

    user_id = str(request.match_info.get("user_id") or "").strip()
    if not user_id:
        return _json_response({"error": "user_id is required"}, status=400)
    target = await db.get_admin_user_by_id(user_id)
    if not target:
        return _json_response({"error": "Admin user not found"}, status=404)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    is_active = bool(payload.get("is_active"))
    if str(target.get("role") or "").strip().lower() == "super_admin" and not is_active:
        return _json_response({"error": "The super admin cannot be disabled from the panel"}, status=400)
    if str(target.get("id")) == str(context["user"].get("id")) and not is_active:
        return _json_response({"error": "You cannot disable your own account"}, status=400)

    updated = await db.update_admin_user(target.get("id"), {"is_active": is_active})
    if not updated:
        return _json_response({"error": "Failed to update admin user"}, status=500)

    await _log_admin_access_event(
        "admin_user_state_changed",
        actor=context["actor"],
        extra={
            "target_user_id": target.get("id"),
            "target_login": target.get("login"),
            "is_active": is_active,
        },
    )
    return _json_response({"ok": True, "user": serialize_admin_user(updated)})


async def create_intent(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    payload = await request.json()
    match_id = str(payload.get("match_id") or "").strip()
    outcome = str(payload.get("outcome") or "").strip().upper()
    sender_wallet = str(payload.get("sender_wallet") or "").strip().upper()
    payment_currency = str(payload.get("payment_currency") or "PRIZM").strip().upper()
    if payment_currency not in ("PRIZM", "USDT"):
        payment_currency = "PRIZM"

    if not match_id or not outcome or not sender_wallet:
        return _json_response({"error": "match_id, outcome, sender_wallet are required"}, status=400)

    matches = _load_matches_cache()
    match = matches.get(match_id)
    if not match:
        return _json_response({"error": "match not found in current cache"}, status=404)

    match_time = _parse_dt(match.get("match_time"))
    now = datetime.now(timezone.utc)
    if bool(match.get("is_live")):
        return _json_response({"error": "LIVE_DISABLED"}, status=400)
    if match_time and match_time.astimezone(timezone.utc) <= now:
        return _json_response({"error": "MATCH_ALREADY_STARTED"}, status=400)

    odds = _extract_odds(match, outcome)
    if not odds:
        return _json_response({"error": "outcome/odds unavailable"}, status=400)

    pending_mode, pending_intent = await _find_wallet_pending_intent(sender_wallet, now)
    if pending_mode == 'single' and pending_intent:
        return _json_response({
            "error": "WALLET_ACTIVE_INTENT_EXISTS",
            "existing_intent": pending_intent,
        }, status=409)
    if pending_mode == 'multiple':
        return _json_response({"error": "WALLET_HAS_MULTIPLE_ACTIVE_INTENTS"}, status=409)

    intent = None
    for _ in range(10):
        intent_hash = _intent_hash(6)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        try:
            await db.create_bet_intent(
                intent_hash=intent_hash,
                match_id=match_id,
                sender_wallet=sender_wallet,
                outcome=outcome,
                odds_fixed=odds,
                expires_at=expires_at,
                payment_currency=payment_currency,
            )
            intent = {
                "intent_hash": intent_hash,
                "odds_fixed": odds,
                "expires_at": expires_at,
                "match_id": match_id,
                "sender_wallet": sender_wallet,
                "payment_currency": payment_currency,
            }
            break
        except Exception:
            continue

    if not intent:
        return _json_response({"error": "failed to create intent"}, status=500)

    return _json_response(intent)


async def get_intent_status(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    intent_hash = str(request.match_info.get("intent_hash") or "").strip().upper()
    if not intent_hash:
        return _json_response({"error": "intent_hash is required"}, status=400)

    intent = await db.get_bet_intent(intent_hash)
    if not intent:
        return _json_response({"error": "intent not found"}, status=404)

    bet_rows = (
        db.client.table("bets")
        .select("*")
        .eq("intent_hash", intent_hash)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    bet = bet_rows[0] if bet_rows else None
    expires_at = _parse_dt(intent.get("expires_at"))
    now = datetime.now(timezone.utc)

    if bet:
        status = bet.get("status", "accepted")
    elif expires_at and expires_at < now:
        status = "expired"
    else:
        status = "awaiting_payment"

    return _json_response({"status": status, "intent": intent, "bet": bet})


async def bet_status(request: web.Request) -> web.Response:
    """Lightweight polling endpoint for frontend bet tracking."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    intent_hash = str(request.match_info.get("intent_hash") or "").strip().upper()
    if not intent_hash:
        return _json_response({"error": "intent_hash is required"}, status=400)

    intent = await db.get_bet_intent(intent_hash)
    if not intent:
        return _json_response({"error": "intent not found"}, status=404)

    bet = None
    try:
        bet_rows = (
            db.client.table("bets")
            .select("tx_id,status,amount_prizm,odds_fixed,payout_amount,payout_tx_id,reject_reason,created_at")
            .eq("intent_hash", intent_hash)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        bet = bet_rows[0] if bet_rows else None
    except Exception:
        pass

    expires_at = _parse_dt(intent.get("expires_at"))
    now = datetime.now(timezone.utc)

    if bet:
        status = str(bet.get("status") or "accepted")
    elif expires_at and expires_at < now:
        status = "expired"
    else:
        status = "awaiting_payment"

    match_id = str(intent.get("match_id") or "").strip()
    match_cache = _load_matches_cache()
    match = match_cache.get(match_id) or {}

    return _json_response({
        "status": status,
        "intent_hash": intent_hash,
        "match_id": match_id,
        "match_label": f"{match.get('team1', '?')} — {match.get('team2', '?')}" if match else None,
        "outcome": intent.get("outcome"),
        "odds_fixed": intent.get("odds_fixed"),
        "amount_prizm": float(bet.get("amount_prizm") or 0) if bet else None,
        "payout_amount": float(bet.get("payout_amount") or 0) if bet else None,
        "payout_tx_id": bet.get("payout_tx_id") if bet else None,
        "reject_reason": bet.get("reject_reason") if bet else None,
        "expires_at": intent.get("expires_at"),
        "score": match.get("score") or None,
    })


async def wallet_dashboard(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = str(request.match_info.get("wallet") or "").strip().upper()
    if not wallet:
        return _json_response({"error": "wallet is required"}, status=400)

    intents = (
        db.client.table("bet_intents")
        .select("*")
        .eq("sender_wallet", wallet)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
        .data
    )
    bets = (
        db.client.table("bets")
        .select("*")
        .eq("sender_wallet", wallet)
        .order("created_at", desc=True)
        .limit(25)
        .execute()
        .data
    )

    now = datetime.now(timezone.utc)
    bet_by_intent = {str(bet.get("intent_hash")): bet for bet in bets if bet.get("intent_hash")}
    waiting_payment = 0
    active_intents = []

    for intent in intents:
        expires_at = _parse_dt(intent.get("expires_at"))
        linked_bet = bet_by_intent.get(str(intent.get("intent_hash")))
        if linked_bet:
            state = linked_bet.get("status", "accepted")
        elif expires_at and expires_at < now:
            state = "expired"
        else:
            state = "awaiting_payment"
            waiting_payment += 1
        active_intents.append({
            "intent_hash": intent.get("intent_hash"),
            "match_id": intent.get("match_id"),
            "outcome": intent.get("outcome"),
            "odds_fixed": intent.get("odds_fixed"),
            "created_at": intent.get("created_at"),
            "expires_at": intent.get("expires_at"),
            "status": state,
        })

    turnover = 0.0
    potential_payout = 0.0
    counts = {
        "accepted": 0,
        "rejected": 0,
        "won": 0,
        "lost": 0,
        "refund_pending": 0,
        "paid": 0,
    }
    for bet in bets:
        status = str(bet.get("status") or "").strip().lower()
        amount = float(bet.get("amount_prizm") or 0)
        odds_fixed = float(bet.get("odds_fixed") or 0)
        if status in ACCEPTED_STATUSES:
            turnover += amount
            potential_payout += amount * odds_fixed
        if status in counts:
            counts[status] += 1

    rank = _rank_preview(
        turnover,
        counts["accepted"] + counts["won"] + counts["lost"] + counts["paid"],
    )

    return _json_response({
        "wallet": wallet,
        "stats": {
            **counts,
            "waiting_payment": waiting_payment,
            "total_bets": len(bets),
            "total_intents": len(intents),
            "turnover_prizm": round(turnover, 2),
            "potential_payout_prizm": round(potential_payout, 2),
        },
        "rank": rank,
        "recent_intents": active_intents,
        "recent_bets": bets,
    })


async def operator_feed(request: web.Request) -> web.Response:
    context, error = await _require_admin(request)
    if error:
        return error

    try:
        limit = int(request.query.get("limit", "60"))
    except ValueError:
        limit = 60
    limit = min(max(limit, 1), 200)
    fetch_limit = min(max(limit * 4, 80), 500)
    status_filter = str(request.query.get("status") or "").strip().lower()
    query = str(request.query.get("q") or "").strip().casefold()

    bets = await db.get_recent_bets(fetch_limit)
    intent_map = await db.get_bet_intents_map([str(bet.get("intent_hash") or "") for bet in bets])

    match_ids = []
    for bet in bets:
        match_id = str(bet.get("match_id") or "").strip()
        if match_id:
            match_ids.append(match_id)
    for intent in intent_map.values():
        match_id = str(intent.get("match_id") or "").strip()
        if match_id:
            match_ids.append(match_id)

    match_cache = _load_matches_cache()
    match_map = await db.get_matches_map(match_ids)
    items = []
    for bet in bets:
        intent_hash = str(bet.get("intent_hash") or "").strip().upper()
        intent = intent_map.get(intent_hash)
        match_id = str(bet.get("match_id") or (intent or {}).get("match_id") or "").strip()
        match = match_map.get(match_id) or match_cache.get(match_id)
        view = build_bet_view(bet, intent=intent, match=match, match_cache=match_cache)
        if status_filter and view["status"] != status_filter:
            continue
        if query and query not in search_blob(view):
            continue
        if not query and not status_filter and _is_operator_noise(view):
            continue
        items.append(view)
        if len(items) >= limit:
            break

    accepted_items = [item for item in items if item["status"] in ACCEPTED_STATUSES]
    turnover = round(sum(item["amount_prizm"] for item in accepted_items), 2)
    potential = round(sum(item["potential_payout_prizm"] for item in accepted_items), 2)
    won_count = sum(1 for item in items if item["status"] == "won")
    lost_count = sum(1 for item in items if item["status"] == "lost")
    paid_count = sum(1 for item in items if item["status"] == "paid")
    paid_amount = round(sum(float(item.get("potential_payout_prizm") or 0) for item in items if item["status"] == "paid"), 2)
    lost_amount = round(sum(float(item.get("amount_prizm") or 0) for item in items if item["status"] == "lost"), 2)
    settled_count = won_count + lost_count + paid_count
    win_rate = round((won_count + paid_count) / settled_count * 100, 1) if settled_count else 0.0
    avg_bet = round(turnover / len(accepted_items), 2) if accepted_items else 0.0
    profit = round(lost_amount - paid_amount, 2)

    stats = {
        "total_items": len(items),
        "accepted_count": sum(1 for item in items if item["status"] == "accepted"),
        "rejected_count": sum(1 for item in items if item["status"] == "rejected"),
        "won_count": won_count,
        "lost_count": lost_count,
        "refund_count": sum(1 for item in items if item["status"] in {"refund_pending", "refunded"}),
        "to_payout_count": won_count,
        "paid_count": paid_count,
        "turnover_prizm": turnover,
        "potential_payout_prizm": potential,
        "paid_amount_prizm": paid_amount,
        "profit_prizm": profit,
        "win_rate": win_rate,
        "avg_bet_prizm": avg_bet,
    }

    return _json_response({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "items": items,
        "meta": {
            "auth_mode": "session",
            "query": query,
            "status_filter": status_filter,
            "current_user": serialize_admin_user(context["user"]),
        },
    })


async def operator_audit_log(request: web.Request) -> web.Response:
    context, error = await _require_admin(request)
    if error:
        return error

    try:
        limit = int(request.query.get("limit", "80"))
    except ValueError:
        limit = 80
    limit = min(max(limit, 1), 200)

    items = await db.get_operator_audit_log(limit)
    return _json_response({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "meta": {
            "auth_mode": "session",
            "db_configured": True,
            "sheets_mirror_enabled": bool(config.GOOGLE_SHEETS_MIRROR_ENABLED and config.GOOGLE_SHEETS_WEBHOOK_URL),
            "current_user": serialize_admin_user(context["user"]),
        },
    })


async def mark_bet_paid(request: web.Request) -> web.Response:
    context, error = await _require_admin(request, {"super_admin", "finance"})
    if error:
        return error

    tx_id = str(request.match_info.get("tx_id") or "").strip()
    if not tx_id:
        return _json_response({"error": "tx_id is required"}, status=400)

    current = await db.get_bet_by_tx_id(tx_id)
    if not current:
        return _json_response({"error": "bet not found"}, status=404)

    current_status = str(current.get("status") or "").strip().lower()
    if current_status not in {"won", "paid"}:
        return _json_response({"error": "Only won or paid bets can be marked as paid"}, status=400)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    payout_tx_id = str(payload.get("payout_tx_id") or "").strip()
    expected_payout = float(current.get("payout_amount") or 0) or round(
        float(current.get("amount_prizm") or 0) * float(current.get("odds_fixed") or 0), 2
    )
    raw_payout_amount = payload.get("payout_amount")
    if raw_payout_amount in (None, ""):
        payout_amount = expected_payout
    else:
        try:
            payout_amount = round(float(raw_payout_amount), 2)
        except (TypeError, ValueError):
            return _json_response({"error": "payout_amount must be numeric"}, status=400)
        if payout_amount <= 0:
            return _json_response({"error": "payout_amount must be positive"}, status=400)
        # Prevent operator from setting arbitrary payout (allow ±10% of expected)
        if expected_payout > 0 and abs(payout_amount - expected_payout) / expected_payout > 0.10:
            return _json_response({
                "error": "payout_amount deviates too much from expected",
                "expected": expected_payout,
            }, status=400)

    updated_rows = await db.mark_bet_paid(tx_id, payout_tx_id=payout_tx_id, payout_amount=payout_amount)
    updated = (updated_rows or [current])[0]
    intent = await db.get_bet_intent(str(updated.get("intent_hash") or "").strip().upper()) if updated.get("intent_hash") else None
    match = await db.get_match_by_id(str(updated.get("match_id") or (intent or {}).get("match_id") or "").strip())
    await notify_payout_sent(updated, intent=dict(intent) if intent else None, match=dict(match) if match else None)
    await log_operator_event(
        "bet_paid",
        updated,
        intent=dict(intent) if intent else None,
        match=dict(match) if match else None,
        actor=context["actor"],
    )
    view = build_bet_view(updated, intent=intent, match=match, match_cache=_load_matches_cache())
    return _json_response({"ok": True, "item": view})


async def admin_wallet_info(request: web.Request) -> web.Response:
    """GET /api/admin/wallet — wallet addresses and hot-wallet balance.

    Accessible to: super_admin, finance, operator, viewer (all authenticated roles).
    The passphrase is NEVER returned — only the wallet address and balance.
    """
    context, error = await _require_admin(request)
    if error:
        return error

    from backend.bot import prizm_api
    from backend.config import config as _cfg

    hot_address = prizm_api.HOT_WALLET
    admin_address = _cfg.PRIZM_ADMIN_WALLET or ""

    balance_info = prizm_api.get_balance()
    passphrase_configured = False
    try:
        enc = await db.get_app_config("hot_wallet_passphrase_enc")
        passphrase_configured = bool(enc)
    except Exception:
        if prizm_api.PASSPHRASE:
            passphrase_configured = True

    # USDT TRC-20 wallet info
    usdt_info = {
        "address": _cfg.USDT_HOT_WALLET or "",
        "enabled": _cfg.USDT_ENABLED,
        "contract": _cfg.USDT_CONTRACT,
    }
    if _cfg.USDT_ENABLED and _cfg.USDT_HOT_WALLET:
        try:
            from backend.bot import usdt_api
            usdt_balance = await usdt_api.get_balance()
            usdt_info["balance"] = usdt_balance
        except Exception:
            usdt_info["balance"] = None

    return _json_response({
        "hot_wallet": {
            "address": hot_address,
            "balance": balance_info.get("balance"),
            "unconfirmed_balance": balance_info.get("unconfirmed"),
            "node": balance_info.get("node"),
            "passphrase_configured": passphrase_configured,
        },
        "admin_wallet": {
            "address": admin_address,
        },
        "usdt_wallet": usdt_info,
        "master_key_configured": bool(_cfg.PRIZM_MASTER_KEY),
    })


async def admin_wallet_set_passphrase(request: web.Request) -> web.Response:
    """POST /api/admin/wallet/passphrase — encrypt and store the hot-wallet passphrase.

    Accessible to: super_admin only.
    Body: { "passphrase": "<raw PRIZM passphrase>" }
    The raw passphrase is encrypted with PRIZM_MASTER_KEY (AES-256-GCM)
    and stored in app_config.  It is NEVER returned or logged.
    """
    context, error = await _require_admin(request, {"super_admin"})
    if error:
        return error

    from backend.config import config as _cfg
    if not _cfg.PRIZM_MASTER_KEY:
        return _json_response(
            {"error": "PRIZM_MASTER_KEY is not configured on the server. Set it in .env first."},
            status=503,
        )

    try:
        body = await request.json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status=400)

    passphrase = str(body.get("passphrase") or "").strip()
    if not passphrase:
        return _json_response({"error": "passphrase is required"}, status=400)
    if len(passphrase) < 8:
        return _json_response({"error": "passphrase is too short (minimum 8 characters)"}, status=400)

    try:
        from backend.utils.wallet_crypto import encrypt_passphrase
        encrypted = encrypt_passphrase(passphrase)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Passphrase encryption failed")
        return _json_response({"error": "Encryption failed. Check server configuration."}, status=500)

    ok = await db.set_app_config("hot_wallet_passphrase_enc", encrypted)
    if not ok:
        return _json_response({"error": "Failed to save encrypted passphrase to DB"}, status=500)

    await log_operator_event(
        "wallet_passphrase_updated",
        {"hot_wallet": prizm_api_wallet()},
        actor=context["actor"],
    )
    return _json_response({"ok": True, "message": "Hot wallet passphrase encrypted and saved."})


def prizm_api_wallet() -> str:
    try:
        from backend.bot import prizm_api
        return prizm_api.HOT_WALLET
    except Exception:
        return ""


async def health(_: web.Request) -> web.Response:
    return _json_response({"ok": True})


async def options_preflight(_: web.Request) -> web.Response:
    return _with_cors(web.Response(status=204))


class _RateLimiter:
    """Simple in-memory rate limiter per IP."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, collections.deque] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits.get(key)
        if q is None:
            q = collections.deque()
            self._hits[key] = q
        while q and q[0] <= now - self._window:
            q.popleft()
        if len(q) >= self._max:
            return False
        q.append(now)
        return True


_login_limiter = _RateLimiter(max_requests=5, window_seconds=60)
_intent_limiter = _RateLimiter(max_requests=config.RATE_LIMIT_REQUESTS, window_seconds=config.RATE_LIMIT_WINDOW)
_passphrase_limiter = _RateLimiter(max_requests=3, window_seconds=60)

RATE_LIMITED_PATHS = {
    "/api/admin/login": _login_limiter,
    "/api/admin/bootstrap": _login_limiter,
    "/api/admin/wallet/passphrase": _passphrase_limiter,
    "/api/intents": _intent_limiter,
}

# Admin-path prefix — used to restrict CORS origin for sensitive endpoints.
_ADMIN_PATH_PREFIX = "/api/admin/"
_ALLOWED_ADMIN_ORIGIN = os.environ.get("ADMIN_CORS_ORIGIN", "").strip()

ADMIN_CORS_HEADERS_STRICT = {
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key, X-Admin-Session, Authorization",
}


def _cors_headers_for(request: web.Request) -> dict[str, str]:
    """Return CORS headers.  Admin endpoints get a restricted origin
    (if ADMIN_CORS_ORIGIN is set) instead of the wildcard."""
    if request.path.startswith(_ADMIN_PATH_PREFIX) and _ALLOWED_ADMIN_ORIGIN:
        return {**ADMIN_CORS_HEADERS_STRICT, "Access-Control-Allow-Origin": _ALLOWED_ADMIN_ORIGIN}
    return CORS_HEADERS


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
        resp.headers.update(_cors_headers_for(request))
        return resp
    # Rate limiting for sensitive endpoints
    limiter = RATE_LIMITED_PATHS.get(request.path)
    if limiter and request.method == "POST":
        ip = client_ip(request)
        if not limiter.is_allowed(ip):
            return _json_response({"error": "Too many requests, try again later"}, status=429)
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    response.headers.update(_cors_headers_for(request))
    return response


async def export_bets_csv(request: web.Request) -> web.Response:
    """Export bets as CSV for accounting."""
    context, error = await _require_admin(request)
    if error:
        return error

    role = str(context["user"].get("role") or "")
    if role not in ("super_admin", "finance"):
        return _json_response({"error": "Forbidden"}, status=403)

    try:
        limit = int(request.query.get("limit", "500"))
    except ValueError:
        limit = 500
    limit = min(max(limit, 1), 5000)
    status_filter = str(request.query.get("status") or "").strip().lower()

    bets = await db.get_recent_bets(limit)
    intent_map = await db.get_bet_intents_map([str(bet.get("intent_hash") or "") for bet in bets])
    match_ids = []
    for bet in bets:
        mid = str(bet.get("match_id") or "").strip()
        if mid:
            match_ids.append(mid)
    match_cache = _load_matches_cache()
    match_map = await db.get_matches_map(match_ids)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "tx_id", "intent_hash", "status", "match", "outcome", "odds",
        "amount_prizm", "potential_payout", "payout_tx_id", "sender_wallet",
        "match_time", "created_at", "reject_reason",
    ])

    for bet in bets:
        intent_hash = str(bet.get("intent_hash") or "").strip().upper()
        intent = intent_map.get(intent_hash) or {}
        match_id = str(bet.get("match_id") or intent.get("match_id") or "").strip()
        match = match_map.get(match_id) or match_cache.get(match_id) or {}
        view = build_bet_view(bet, intent=intent, match=match, match_cache=match_cache)
        if status_filter and view["status"] != status_filter:
            continue
        writer.writerow([
            view["tx_id"],
            view["intent_hash"],
            view["status"],
            view["match_label"],
            view["outcome_label"],
            view["odds_fixed"],
            view["amount_prizm"],
            view["potential_payout_prizm"],
            view["payout_tx_id"],
            view["sender_wallet"],
            view["match_time"],
            view["created_at"],
            view.get("reject_reason", ""),
        ])

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    resp = web.Response(
        text=output.getvalue(),
        content_type="text/csv",
        charset="utf-8",
    )
    resp.headers["Content-Disposition"] = f'attachment; filename="prizmbet_bets_{now_str}.csv"'
    resp.headers.update(CORS_HEADERS)
    return resp


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/health", health)
    app.router.add_get("/api/admin/bootstrap-state", bootstrap_state)
    app.router.add_post("/api/admin/bootstrap", bootstrap_admin)
    app.router.add_post("/api/admin/login", admin_login)
    app.router.add_post("/api/admin/logout", admin_logout)
    app.router.add_get("/api/admin/me", admin_me)
    app.router.add_get("/api/admin/users", admin_users)
    app.router.add_post("/api/admin/users", admin_create_user)
    app.router.add_post("/api/admin/users/{user_id}/set-active", admin_set_user_active)
    app.router.add_post("/api/intents", create_intent)
    app.router.add_get("/api/intents/{intent_hash}", get_intent_status)
    app.router.add_get("/api/bet-status/{intent_hash}", bet_status)
    app.router.add_get("/api/wallets/{wallet}/dashboard", wallet_dashboard)
    app.router.add_get("/api/admin/feed", operator_feed)
    app.router.add_get("/api/admin/audit-log", operator_audit_log)
    app.router.add_post("/api/admin/bets/{tx_id}/mark-paid", mark_bet_paid)
    app.router.add_get("/api/admin/wallet", admin_wallet_info)
    app.router.add_post("/api/admin/wallet/passphrase", admin_wallet_set_passphrase)
    app.router.add_get("/api/admin/export-csv", export_bets_csv)

    # Serve frontend static files
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if frontend_dir.is_dir():
        async def _root_redirect(_req):
            raise web.HTTPFound("/index.html")
        app.router.add_get("/", _root_redirect)
        app.router.add_static("/", frontend_dir, show_index=False)

    return app


if __name__ == "__main__":
    db.init()
    web.run_app(create_app(), host="0.0.0.0", port=8081)
