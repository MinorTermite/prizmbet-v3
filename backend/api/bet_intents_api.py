# -*- coding: utf-8 -*-
"""Bet Intent API for public v3 flow and operator auth."""
from __future__ import annotations

import collections
import asyncio
import csv
import io
import json
import logging
import os
import re
import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aiohttp import web

logger = logging.getLogger(__name__)

from backend.config import config
from backend.db.supabase_client import db
from backend.utils.admin_auth import (
    client_ip,
    hash_password,
    issue_session_token,
    is_owner_user,
    normalize_email,
    normalize_login,
    normalize_role,
    role_can_manage_users,
    serialize_admin_user,
    session_expires_at,
    session_token_hash,
    validate_email,
    validate_login,
    validate_password,
    verify_password,
)
from backend.bot.gamification import (
    LEVELS as _GAMIFICATION_LEVELS,
    QUEST_BY_ID as _QUEST_BY_ID,
    apply_settlement_bonuses as _gamification_apply_bonuses,
    finalize_weekly_leaderboard as _gamification_finalize_weekly,
    increment_quest_progress as _gamification_increment_quest,
    on_bet_settled as _gamification_on_bet_settled,
    spin_roulette as _gamification_spin_roulette,
)
from backend.bot.v3_settler import determine_bet_result
from backend.utils.bet_views import ACCEPTED_STATUSES, build_bet_view, search_blob
from backend.utils.operator_alerts import notify_bet_settled, notify_payout_sent
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
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key, X-Admin-Session, Authorization",
}

_DEFAULT_PUBLIC_CORS_ORIGINS = (
    "https://prizmbet.net",
    "https://www.prizmbet.net",
)


def _csv_env(name: str, default: tuple[str, ...] = ()) -> set[str]:
    raw = os.environ.get(name, "").strip()
    values = raw.split(",") if raw else default
    return {str(value).strip().rstrip("/") for value in values if str(value).strip()}


_ALLOWED_PUBLIC_ORIGINS = _csv_env("PUBLIC_CORS_ORIGINS", _DEFAULT_PUBLIC_CORS_ORIGINS)

MATCHES_CACHE_PATH = Path(__file__).resolve().parents[2] / "frontend" / "matches.json"
INTENT_HASH_LENGTH = 12
INTENT_HASH_RE = re.compile(r"^[A-Z0-9]{6,32}$")
WALLET_RE = re.compile(r"^[A-Z0-9:_-]{3,96}$")
WALLET_VERIFICATION_CODE_RE = re.compile(r"^PB-[A-Z0-9]{6,12}$")
WALLET_VERIFICATION_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
WALLET_VERIFICATION_CODE_LENGTH = 8
MANUAL_SCORE_RE = re.compile(r"^\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*$")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://cookieconsent.orestbida.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https://www.googletagmanager.com; "
        "connect-src 'self' https://www.googletagmanager.com; "
        "frame-src 'self' https://www.googletagmanager.com; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


def _with_cors(response: web.StreamResponse) -> web.StreamResponse:
    response.headers.update(CORS_HEADERS)
    response.headers.update(SECURITY_HEADERS)
    return response


def _json_response(payload: dict[str, Any], status: int = 200) -> web.Response:
    return web.json_response(payload, status=status)


def _normalize_intent_hash(value: Any) -> str:
    intent_hash = str(value or "").strip().upper()
    return intent_hash if INTENT_HASH_RE.fullmatch(intent_hash) else ""


def _normalize_wallet(value: Any) -> str:
    wallet = str(value or "").strip().upper()
    return wallet if WALLET_RE.fullmatch(wallet) else ""


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
    if not value or value in ("-", "вЂ”", "0", "0.00"):
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _build_match_snapshot(match: dict[str, Any], *, outcome: str, odds: float) -> dict[str, Any]:
    match_id = str(match.get("id") or match.get("match_id") or "").strip()
    snapshot = {
        "match_id": match_id,
        "id": match_id,
        "outcome": str(outcome or "").strip().upper(),
        "odds": round(float(odds or 0), 4),
        "team1": match.get("team1") or match.get("home_team") or "",
        "team2": match.get("team2") or match.get("away_team") or "",
        "league": match.get("league") or "",
        "sport": match.get("sport") or "",
        "match_time": match.get("match_time") or "",
        "date": match.get("date") or "",
        "time": match.get("time") or "",
        "source": match.get("source") or "",
        "match_url": match.get("match_url") or "",
        "is_live": bool(match.get("is_live")),
        "score": match.get("score") or "",
    }
    for key in (
        "p1",
        "x",
        "p2",
        "p1x",
        "p12",
        "px2",
        "total_value",
        "total_over",
        "total_under",
        "handicap_1_value",
        "handicap_1",
        "handicap_2_value",
        "handicap_2",
    ):
        if key in match:
            snapshot[key] = match.get(key)
    return snapshot


def _intent_hash(length: int = INTENT_HASH_LENGTH) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def _verification_code() -> str:
    suffix = "".join(secrets.choice(WALLET_VERIFICATION_CODE_ALPHABET) for _ in range(WALLET_VERIFICATION_CODE_LENGTH))
    return f"PB-{suffix}"


def _verification_amount() -> float:
    return round(max(float(config.WALLET_VERIFICATION_AMOUNT_PRIZM or 1), 0.00000001), 8)


def _verification_wallet() -> str:
    return _normalize_wallet(config.PRIZM_VERIFICATION_WALLET or config.PRIZM_HOT_WALLET)


def _public_verification_challenge(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "code": str(row.get("code") or ""),
        "amount_prizm": float(row.get("amount_prizm") or _verification_amount()),
        "recipient_wallet": str(row.get("recipient_wallet") or _verification_wallet()),
        "status": str(row.get("status") or "pending"),
        "expires_at": row.get("expires_at"),
        "created_at": row.get("created_at"),
    }


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
    return ""


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


async def _require_owner(request: web.Request) -> tuple[dict[str, Any] | None, web.Response | None]:
    """Require the configured owner identity, not just a privileged role.

    Financial mutation endpoints must be controlled by the person defined in
    SUPER_ADMIN_LOGIN / SUPER_ADMIN_EMAIL. A copied "finance" or "super_admin"
    role is not sufficient for wallet/passphrase/payout-control changes.
    """
    context, error = await _require_admin(request)
    if error:
        return None, error
    if not is_owner_user(context["user"]):
        return None, _json_response({"error": "Owner identity required"}, status=403)
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
    sender_wallet = _normalize_wallet(payload.get("sender_wallet"))
    payment_currency = str(payload.get("payment_currency") or "PRIZM").strip().upper()
    if payment_currency not in ("PRIZM", "USDT"):
        payment_currency = "PRIZM"

    if not sender_wallet:
        return _json_response({"error": "sender_wallet is required or invalid"}, status=400)

    bet_type = str(payload.get("bet_type") or "single").strip().lower()
    if bet_type not in ("single", "express"):
        bet_type = "single"

    matches = _load_matches_cache()
    now = datetime.now(timezone.utc)

    # ---------- EXPRESS PATH ----------
    if bet_type == "express":
        legs_raw = payload.get("legs") or []
        if not isinstance(legs_raw, list) or len(legs_raw) < 2:
            return _json_response({"error": "express requires >= 2 legs"}, status=400)
        if len(legs_raw) > 12:
            return _json_response({"error": "express supports up to 12 legs"}, status=400)

        seen_match_ids: set[str] = set()
        normalized_legs: list[dict] = []
        combined_odds = 1.0

        for raw_leg in legs_raw:
            if not isinstance(raw_leg, dict):
                return _json_response({"error": "invalid leg structure"}, status=400)
            leg_match_id = str(raw_leg.get("match_id") or "").strip()
            leg_outcome = str(raw_leg.get("outcome") or "").strip().upper()
            if not leg_match_id or not leg_outcome:
                return _json_response({"error": "leg requires match_id and outcome"}, status=400)
            if leg_match_id in seen_match_ids:
                return _json_response({"error": "DUPLICATE_MATCH_IN_EXPRESS"}, status=400)
            seen_match_ids.add(leg_match_id)

            leg_match = matches.get(leg_match_id)
            if not leg_match:
                return _json_response({"error": f"match not found: {leg_match_id}"}, status=404)
            if bool(leg_match.get("is_live")):
                return _json_response({"error": "LIVE_DISABLED"}, status=400)
            leg_match_time = _parse_dt(leg_match.get("match_time"))
            if leg_match_time and leg_match_time.astimezone(timezone.utc) <= now:
                return _json_response({"error": f"MATCH_ALREADY_STARTED: {leg_match_id}"}, status=400)

            leg_odds = _extract_odds(leg_match, leg_outcome)
            if not leg_odds:
                return _json_response({"error": f"outcome/odds unavailable: {leg_match_id}/{leg_outcome}"}, status=400)

            combined_odds *= float(leg_odds)
            normalized_legs.append({
                **_build_match_snapshot(leg_match, outcome=leg_outcome, odds=float(leg_odds)),
                "match_id": leg_match_id,
                "id": leg_match_id,
            })

        if combined_odds > 100.0:
            combined_odds = 100.0
        combined_odds = round(combined_odds, 4)

        pending_mode, pending_intent = await _find_wallet_pending_intent(sender_wallet, now)
        if pending_mode == 'single' and pending_intent:
            return _json_response({
                "error": "WALLET_ACTIVE_INTENT_EXISTS",
                "existing_intent": pending_intent,
            }, status=409)
        if pending_mode == 'multiple':
            return _json_response({"error": "WALLET_HAS_MULTIPLE_ACTIVE_INTENTS"}, status=409)

        anchor_match_id = normalized_legs[0]["match_id"]
        anchor_outcome = "EXPRESS"

        intent = None
        for _ in range(10):
            intent_hash = _intent_hash()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            try:
                await db.create_bet_intent(
                    intent_hash=intent_hash,
                    match_id=anchor_match_id,
                    sender_wallet=sender_wallet,
                    outcome=anchor_outcome,
                    odds_fixed=combined_odds,
                    expires_at=expires_at,
                    payment_currency=payment_currency,
                    bet_type="express",
                    express_legs=normalized_legs,
                )
                intent = {
                    "intent_hash": intent_hash,
                    "odds_fixed": combined_odds,
                    "expires_at": expires_at,
                    "match_id": anchor_match_id,
                    "sender_wallet": sender_wallet,
                    "payment_currency": payment_currency,
                    "bet_type": "express",
                    "legs": normalized_legs,
                }
                break
            except Exception:
                continue

        if not intent:
            return _json_response({"error": "failed to create intent"}, status=500)
        return _json_response(intent)

    # ---------- SINGLE PATH ----------
    match_id = str(payload.get("match_id") or "").strip()
    outcome = str(payload.get("outcome") or "").strip().upper()

    if not match_id or not outcome:
        return _json_response({"error": "match_id, outcome, sender_wallet are required"}, status=400)

    match = matches.get(match_id)
    if not match:
        return _json_response({"error": "match not found in current cache"}, status=404)

    match_time = _parse_dt(match.get("match_time"))
    if bool(match.get("is_live")):
        return _json_response({"error": "LIVE_DISABLED"}, status=400)
    if match_time and match_time.astimezone(timezone.utc) <= now:
        return _json_response({"error": "MATCH_ALREADY_STARTED"}, status=400)

    odds = _extract_odds(match, outcome)
    if not odds:
        return _json_response({"error": "outcome/odds unavailable"}, status=400)
    single_snapshot = _build_match_snapshot(match, outcome=outcome, odds=odds)

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
        intent_hash = _intent_hash()
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
                bet_type="single",
                express_legs=[single_snapshot],
            )
            intent = {
                "intent_hash": intent_hash,
                "odds_fixed": odds,
                "expires_at": expires_at,
                "match_id": match_id,
                "sender_wallet": sender_wallet,
                "payment_currency": payment_currency,
                "bet_type": "single",
                "match_snapshot": single_snapshot,
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

    intent_hash = _normalize_intent_hash(request.match_info.get("intent_hash"))
    if not intent_hash:
        return _json_response({"error": "intent_hash is required or invalid"}, status=400)

    intent = await db.get_bet_intent(intent_hash)
    if not intent:
        return _json_response({"error": "intent not found"}, status=404)

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
    expires_at = _parse_dt(intent.get("expires_at"))
    now = datetime.now(timezone.utc)

    if bet:
        status = bet.get("status", "accepted")
    elif expires_at and expires_at < now:
        status = "expired"
    else:
        status = "awaiting_payment"

    safe_intent = {
        "intent_hash": intent.get("intent_hash"),
        "match_id": intent.get("match_id"),
        "outcome": intent.get("outcome"),
        "odds_fixed": intent.get("odds_fixed"),
        "expires_at": intent.get("expires_at"),
        "payment_currency": intent.get("payment_currency"),
        "bet_type": intent.get("bet_type"),
    }
    return _json_response({"status": status, "intent": safe_intent, "bet": bet})


async def bet_status(request: web.Request) -> web.Response:
    """Lightweight polling endpoint for frontend bet tracking."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    intent_hash = _normalize_intent_hash(request.match_info.get("intent_hash"))
    if not intent_hash:
        return _json_response({"error": "intent_hash is required or invalid"}, status=400)

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
        "match_label": f"{match.get('team1', '?')} вЂ” {match.get('team2', '?')}" if match else None,
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

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)

    intents = (
        db.client.table("bet_intents")
        .select("intent_hash,match_id,outcome,odds_fixed,created_at,expires_at,payment_currency,bet_type")
        .eq("sender_wallet", wallet)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
        .data
    )
    bets = (
        db.client.table("bets")
        .select("intent_hash,match_id,outcome,bet_type,odds_fixed,amount_prizm,payout_amount,status,reject_reason,created_at")
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


def _parse_manual_score(raw_score: Any) -> tuple[int, int] | None:
    match = MANUAL_SCORE_RE.fullmatch(str(raw_score or "").strip())
    if not match:
        return None
    home_goals = int(match.group(1))
    away_goals = int(match.group(2))
    if home_goals > 50 or away_goals > 50:
        return None
    return home_goals, away_goals


def _intent_express_legs(intent: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not intent:
        return []
    legs = intent.get("express_legs")
    return legs if isinstance(legs, list) else []


def _manual_match_payload(
    current: dict[str, Any],
    intent: dict[str, Any] | None,
    match: dict[str, Any] | None,
    score: str,
) -> dict[str, Any]:
    payload = dict(match or {})
    match_id = str(current.get("match_id") or (intent or {}).get("match_id") or payload.get("id") or "").strip()
    if not payload:
        for leg in _intent_express_legs(intent):
            leg_match_id = str(leg.get("match_id") or leg.get("id") or "").strip()
            if leg_match_id and leg_match_id == match_id:
                payload = dict(leg)
                break
    if match_id:
        payload.setdefault("id", match_id)
        payload.setdefault("match_id", match_id)
    payload["score"] = score
    return payload


async def manual_settle_bet(request: web.Request) -> web.Response:
    context, error = await _require_owner(request)
    if error:
        return error

    tx_id = str(request.match_info.get("tx_id") or "").strip()
    if not tx_id:
        return _json_response({"error": "tx_id is required"}, status=400)

    current = await db.get_bet_by_tx_id(tx_id)
    if not current:
        return _json_response({"error": "bet not found"}, status=404)

    current_status = str(current.get("status") or "").strip().lower()
    if current_status != "accepted":
        return _json_response({"error": "Only accepted bets can be settled manually"}, status=400)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    score_pair = _parse_manual_score(payload.get("score"))
    if not score_pair:
        return _json_response({"error": "score must use home:away format, for example 2:1"}, status=400)
    score = f"{score_pair[0]}:{score_pair[1]}"

    intent = await db.get_bet_intent(str(current.get("intent_hash") or "").strip().upper()) if current.get("intent_hash") else None
    legs = _intent_express_legs(dict(intent) if intent else None)
    if len(legs) > 1 or str((intent or {}).get("bet_type") or current.get("bet_type") or "").strip().lower() == "express":
        return _json_response({"error": "Manual score settlement supports single bets only"}, status=400)

    outcome = str((intent or {}).get("outcome") or current.get("outcome") or "").strip()
    verdict = determine_bet_result(outcome, score_pair[0], score_pair[1])
    if verdict is None:
        return _json_response({"error": "Unsupported outcome for manual settlement"}, status=400)

    amount_prizm = float(current.get("amount_prizm") or current.get("amount") or 0)
    odds_fixed = float(current.get("odds_fixed") or (intent or {}).get("odds_fixed") or 0)
    base_payout = round(amount_prizm * odds_fixed, 2) if verdict else 0.0
    sender_wallet = str(current.get("sender_wallet") or (intent or {}).get("sender_wallet") or "").strip().upper()
    bonus_result = await _gamification_apply_bonuses(
        sender_wallet,
        tx_id,
        amount_prizm,
        base_payout,
        verdict,
    )
    payout_amount = float(bonus_result.get("payout_amount") or base_payout)
    status = "won" if verdict or payout_amount > 0 else "lost"
    settlement_reason = "CASHBACK_BONUS" if (not verdict and payout_amount > 0) else None

    updated_rows = await db.update_bet_settlement(
        tx_id,
        status=status,
        payout_amount=payout_amount,
        reason=settlement_reason,
    )
    updated = (updated_rows or [{**current, "status": status, "payout_amount": payout_amount}])[0]
    match = await db.get_match_by_id(str(current.get("match_id") or (intent or {}).get("match_id") or "").strip())
    match_payload = _manual_match_payload(current, dict(intent) if intent else None, dict(match) if match else None, score)

    await log_operator_event(
        "bet_won" if verdict else "bet_lost",
        updated,
        intent=dict(intent) if intent else None,
        match=match_payload,
        actor=context["actor"],
        extra={
            "manual": True,
            "score": score,
            "bonus_result": bonus_result,
        },
    )
    await notify_bet_settled(updated, intent=dict(intent) if intent else None, match=match_payload)

    try:
        if sender_wallet:
            asyncio.create_task(_gamification_on_bet_settled(
                wallet=sender_wallet,
                bet_tx_id=tx_id,
                amount_prizm=amount_prizm,
                odds=odds_fixed,
                won=verdict,
                league=str(match_payload.get("league") or ""),
                sport=str(match_payload.get("sport") or ""),
            ))
    except Exception:
        pass

    view = build_bet_view(updated, intent=intent, match=match_payload, match_cache=_load_matches_cache())
    return _json_response({"ok": True, "item": view})


async def mark_bet_paid(request: web.Request) -> web.Response:
    context, error = await _require_owner(request)
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
    if expected_payout <= 0:
        # Legacy/manually-settled bets without amount/odds cannot be marked paid blindly:
        # without an expected value, the ±10% deviation guard below would let owner write
        # any payout_amount. Require manual_settle first (or db cleanup) to set amount/odds.
        return _json_response({
            "error": "cannot mark bet paid: bet has zero/missing amount or odds",
        }, status=400)
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
        # Prevent operator from setting arbitrary payout (allow В±10% of expected)
        if expected_payout > 0 and abs(payout_amount - expected_payout) / expected_payout > 0.10:
            return _json_response({
                "error": "payout_amount deviates too much from expected",
                "expected": expected_payout,
            }, status=400)

    updated_rows = await db.mark_bet_paid(tx_id, payout_tx_id=payout_tx_id, payout_amount=payout_amount)
    # Idempotent: empty rows means DB guard (status='won' AND payout_tx_id IS NULL)
    # did not match — bet was already paid. Skip notify/log to avoid duplicate
    # Telegram messages and operator events on retry.
    already_paid = not updated_rows
    updated = (updated_rows or [current])[0]
    intent = await db.get_bet_intent(str(updated.get("intent_hash") or "").strip().upper()) if updated.get("intent_hash") else None
    match = await db.get_match_by_id(str(updated.get("match_id") or (intent or {}).get("match_id") or "").strip())
    if not already_paid:
        await notify_payout_sent(updated, intent=dict(intent) if intent else None, match=dict(match) if match else None)
        await log_operator_event(
            "bet_paid",
            updated,
            intent=dict(intent) if intent else None,
            match=dict(match) if match else None,
            actor=context["actor"],
        )
    view = build_bet_view(updated, intent=intent, match=match, match_cache=_load_matches_cache())
    return _json_response({"ok": True, "item": view, "already_paid": already_paid})


async def _wallet_status_payload() -> dict[str, Any]:
    from backend.bot import auto_payout, prizm_api, wallet_sweep
    from backend.config import config as _cfg

    balance_info = prizm_api.get_balance()
    passphrase_configured = False
    try:
        enc = await db.get_app_config("hot_wallet_passphrase_enc")
        passphrase_configured = bool(enc)
    except Exception:
        if prizm_api.PASSPHRASE:
            passphrase_configured = True

    return {
        "emergency_stop": await db.is_emergency_stop_enabled(),
        "hot_wallet": {
            "address": prizm_api.HOT_WALLET,
            "balance": balance_info.get("balance"),
            "unconfirmed_balance": balance_info.get("unconfirmed"),
            "node": balance_info.get("node"),
            "passphrase_configured": passphrase_configured,
        },
        "admin_wallet": {
            "address": _cfg.PRIZM_ADMIN_WALLET or "",
        },
        "cold_wallet": {
            "address": wallet_sweep.get_runtime_status().get("cold_wallet") or "",
        },
        "payout_runtime": auto_payout.get_runtime_status(),
        "sweep_runtime": wallet_sweep.get_runtime_status(),
        "pending_payout_total": await db.get_pending_payout_total(),
        "reserved_payout_total": await db.get_reserved_payout_total(),
        "recent_financial_events": await db.get_financial_events(limit=20),
        "master_key_configured": bool(_cfg.PRIZM_MASTER_KEY),
    }


async def admin_wallet_info(request: web.Request) -> web.Response:
    """GET /api/admin/wallet вЂ” wallet addresses and hot-wallet balance.

    Accessible to: super_admin, finance, operator, viewer (all authenticated roles).
    The passphrase is NEVER returned вЂ” only the wallet address and balance.
    """
    context, error = await _require_admin(request)
    if error:
        return error

    status_payload = await _wallet_status_payload()

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
        "emergency_stop": status_payload.get("emergency_stop"),
        "pending_payout_total": status_payload.get("pending_payout_total"),
        "reserved_payout_total": status_payload.get("reserved_payout_total"),
    })


async def admin_wallet_set_passphrase(request: web.Request) -> web.Response:
    """POST /api/admin/wallet/passphrase вЂ” encrypt and store the hot-wallet passphrase.

    Accessible to: configured owner only.
    Body: { "passphrase": "<raw PRIZM passphrase>" }
    The raw passphrase is encrypted with PRIZM_MASTER_KEY (AES-256-GCM)
    and stored in app_config.  It is NEVER returned or logged.
    """
    context, error = await _require_owner(request)
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


async def admin_wallet_status(request: web.Request) -> web.Response:
    context, error = await _require_admin(request)
    if error:
        return error

    payload = await _wallet_status_payload()
    payload["current_user"] = serialize_admin_user(context["user"])
    return _json_response(payload)


async def admin_wallet_emergency_stop(request: web.Request) -> web.Response:
    context, error = await _require_owner(request)
    if error:
        return error

    ok = await db.set_emergency_stop_enabled(True)
    if not ok:
        return _json_response({"error": "Failed to enable finance emergency stop"}, status=500)

    await _log_admin_access_event(
        "wallet_emergency_stop_enabled",
        actor=context["actor"],
        extra={"reason": "manual emergency stop"},
    )
    payload = await _wallet_status_payload()
    return _json_response({"ok": True, "message": "Finance emergency stop enabled", "status": payload})


async def admin_wallet_resume(request: web.Request) -> web.Response:
    context, error = await _require_owner(request)
    if error:
        return error

    ok = await db.set_emergency_stop_enabled(False)
    if not ok:
        return _json_response({"error": "Failed to disable finance emergency stop"}, status=500)

    from backend.bot import auto_payout

    auto_payout.reset_runtime_guards()
    await _log_admin_access_event(
        "wallet_emergency_stop_disabled",
        actor=context["actor"],
        extra={"reason": "manual resume"},
    )
    payload = await _wallet_status_payload()
    return _json_response({"ok": True, "message": "Finance operations resumed", "status": payload})


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
    """Bounded in-memory rate limiter per key."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60, max_keys: int | None = None):
        self._max = max(int(max_requests or 1), 1)
        self._window = max(int(window_seconds or 1), 1)
        self._max_keys = max(int(max_keys or config.RATE_LIMIT_MAX_KEYS or 10000), 100)
        self._hits: dict[str, collections.deque] = {}
        self._last_seen: dict[str, float] = {}

    def _prune(self, now: float) -> None:
        stale = [key for key, seen in self._last_seen.items() if seen <= now - self._window]
        for key in stale:
            self._hits.pop(key, None)
            self._last_seen.pop(key, None)
        if len(self._hits) <= self._max_keys:
            return
        overflow = len(self._hits) - self._max_keys
        for key, _ in sorted(self._last_seen.items(), key=lambda item: item[1])[:overflow]:
            self._hits.pop(key, None)
            self._last_seen.pop(key, None)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        key = str(key or "unknown")[:180]
        q = self._hits.get(key)
        if q is None:
            if len(self._hits) >= self._max_keys:
                self._prune(now)
            q = collections.deque()
            self._hits[key] = q
        while q and q[0] <= now - self._window:
            q.popleft()
        self._last_seen[key] = now
        if len(q) >= self._max:
            return False
        q.append(now)
        return True


_login_limiter = _RateLimiter(max_requests=5, window_seconds=60)
_intent_limiter = _RateLimiter(max_requests=config.RATE_LIMIT_REQUESTS, window_seconds=config.RATE_LIMIT_WINDOW)
_passphrase_limiter = _RateLimiter(max_requests=3, window_seconds=60)
_api_limiter = _RateLimiter(max_requests=config.API_RATE_LIMIT_REQUESTS, window_seconds=config.API_RATE_LIMIT_WINDOW)
_status_limiter = _RateLimiter(max_requests=config.STATUS_RATE_LIMIT_REQUESTS, window_seconds=config.STATUS_RATE_LIMIT_WINDOW)
_admin_limiter = _RateLimiter(max_requests=config.ADMIN_RATE_LIMIT_REQUESTS, window_seconds=config.ADMIN_RATE_LIMIT_WINDOW)
_gamification_limiter = _RateLimiter(max_requests=config.GAMIFICATION_RATE_LIMIT_REQUESTS, window_seconds=config.GAMIFICATION_RATE_LIMIT_WINDOW)
_wallet_verification_limiter = _RateLimiter(max_requests=6, window_seconds=300)

RATE_LIMITED_PATHS: dict[str, tuple[_RateLimiter, set[str]]] = {
    "/api/admin/login": (_login_limiter, {"POST"}),
    "/api/admin/bootstrap": (_login_limiter, {"POST"}),
    "/api/admin/wallet/passphrase": (_passphrase_limiter, {"POST"}),
    "/api/intents": (_intent_limiter, {"POST"}),
}

# Admin-path prefix вЂ” used to restrict CORS origin for sensitive endpoints.
_ADMIN_PATH_PREFIX = "/api/admin/"
_ALLOWED_ADMIN_ORIGIN = os.environ.get("ADMIN_CORS_ORIGIN", "").strip()

ADMIN_CORS_HEADERS_STRICT = {
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key, X-Admin-Session, Authorization",
}


def _cors_headers_for(request: web.Request) -> dict[str, str]:
    """Return least-privilege CORS headers. Requests without Origin are not browser CORS."""
    origin = str(request.headers.get("Origin") or "").strip().rstrip("/")
    if request.path.startswith(_ADMIN_PATH_PREFIX):
        if _ALLOWED_ADMIN_ORIGIN and origin == _ALLOWED_ADMIN_ORIGIN:
            return {
                **ADMIN_CORS_HEADERS_STRICT,
                "Access-Control-Allow-Origin": _ALLOWED_ADMIN_ORIGIN,
                "Vary": "Origin",
            }
        return ADMIN_CORS_HEADERS_STRICT

    headers = dict(CORS_HEADERS)
    if origin and origin in _ALLOWED_PUBLIC_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return headers


def _limiter_for(request: web.Request) -> _RateLimiter | None:
    exact = RATE_LIMITED_PATHS.get(request.path)
    if exact and request.method in exact[1]:
        return exact[0]
    if not request.path.startswith("/api/"):
        return None
    if request.path.startswith("/api/intents/") or request.path.startswith("/api/bet-status/"):
        return _status_limiter
    if request.path.startswith("/api/wallets/") and request.path.endswith("/dashboard"):
        return _status_limiter
    if request.path.startswith("/api/wallets/") and "/verification" in request.path:
        return _status_limiter if request.method == "GET" else _wallet_verification_limiter
    if request.path.startswith("/api/player/") or request.path.startswith("/api/raffles/"):
        return _gamification_limiter
    if request.path.startswith(_ADMIN_PATH_PREFIX):
        return _admin_limiter
    return _api_limiter


def _finalize_response(request: web.Request, response: web.StreamResponse) -> web.StreamResponse:
    response.headers.update(SECURITY_HEADERS)
    response.headers.update(_cors_headers_for(request))
    if request.path.startswith(_ADMIN_PATH_PREFIX):
        response.headers["Cache-Control"] = "no-store"
    return response


@web.middleware
async def cors_middleware(request: web.Request, handler):
    origin = str(request.headers.get("Origin") or "").strip().rstrip("/")
    if request.path.startswith(_ADMIN_PATH_PREFIX):
        if origin and (not _ALLOWED_ADMIN_ORIGIN or origin != _ALLOWED_ADMIN_ORIGIN):
            return _finalize_response(request, _json_response({"error": "Admin origin is not allowed"}, status=403))
    elif origin and origin not in _ALLOWED_PUBLIC_ORIGINS:
        return _finalize_response(request, _json_response({"error": "CORS origin is not allowed"}, status=403))

    if request.method == "OPTIONS":
        if request.path.startswith(_ADMIN_PATH_PREFIX):
            if not _ALLOWED_ADMIN_ORIGIN or origin != _ALLOWED_ADMIN_ORIGIN:
                return _finalize_response(request, _json_response({"error": "CORS origin is not allowed"}, status=403))
        elif origin and origin not in _ALLOWED_PUBLIC_ORIGINS:
            return _finalize_response(request, _json_response({"error": "CORS origin is not allowed"}, status=403))
        resp = web.Response(status=204)
        return _finalize_response(request, resp)
    limiter = _limiter_for(request)
    if limiter:
        ip = client_ip(request)
        if not limiter.is_allowed(ip):
            return _finalize_response(request, _json_response({"error": "Too many requests, try again later"}, status=429))
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    return _finalize_response(request, response)


async def _wallet_is_verified(wallet: str) -> bool:
    if not wallet:
        return False
    return bool(await db.get_wallet_verification(wallet))


async def _wallet_verification_payload(wallet: str) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    verified_row = await db.get_wallet_verification(wallet)
    challenge = None
    if not verified_row:
        challenge = await db.get_pending_wallet_verification_challenge(wallet, now_iso)
    return {
        "verified": bool(verified_row),
        "verified_at": verified_row.get("last_verified_at") if verified_row else None,
        "method": "prizm_transfer_code",
        "amount_prizm": _verification_amount(),
        "recipient_wallet": _verification_wallet(),
        "challenge": _public_verification_challenge(challenge),
    }


async def wallet_verification_status(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)

    return _json_response({
        "ok": True,
        "wallet": wallet,
        "verification": await _wallet_verification_payload(wallet),
    })


async def wallet_verification_challenge(request: web.Request) -> web.Response:
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)

    recipient_wallet = _verification_wallet()
    if not recipient_wallet:
        return _json_response({"error": "Verification wallet is not configured"}, status=500)

    if await _wallet_is_verified(wallet):
        return _json_response({
            "ok": True,
            "wallet": wallet,
            "verification": await _wallet_verification_payload(wallet),
        })

    now = datetime.now(timezone.utc)
    await db.expire_wallet_verification_challenges(wallet)
    existing = await db.get_pending_wallet_verification_challenge(wallet, now.isoformat())
    if existing:
        return _json_response({
            "ok": True,
            "wallet": wallet,
            "verification": await _wallet_verification_payload(wallet),
        })

    ttl_minutes = max(int(config.WALLET_VERIFICATION_TTL_MINUTES or 30), 5)
    expires_at = now + timedelta(minutes=ttl_minutes)
    amount = _verification_amount()
    ip = client_ip(request)[:120]
    user_agent = str(request.headers.get("User-Agent") or "")[:500]

    for _ in range(5):
        code = _verification_code()
        if not WALLET_VERIFICATION_CODE_RE.fullmatch(code):
            continue
        row = await db.create_wallet_verification_challenge({
            "wallet": wallet,
            "code": code,
            "amount_prizm": amount,
            "recipient_wallet": recipient_wallet,
            "expires_at": expires_at.isoformat(),
            "requested_ip": ip,
            "user_agent": user_agent,
        })
        if row:
            return _json_response({
                "ok": True,
                "wallet": wallet,
                "verification": {
                    "verified": False,
                    "verified_at": None,
                    "method": "prizm_transfer_code",
                    "amount_prizm": amount,
                    "recipient_wallet": recipient_wallet,
                    "challenge": _public_verification_challenge(row),
                },
            })

    return _json_response({"error": "Failed to create verification challenge"}, status=500)


async def export_bets_csv(request: web.Request) -> web.Response:
    """Export bets as CSV for accounting."""
    context, error = await _require_owner(request)
    if error:
        return error

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
    resp.headers["Content-Disposition"] = f'attachment; filename="one_prizmbet_bets_{now_str}.csv"'
    return resp


# ── Gamification helpers ───────────────────────────────────────────────────────

def _enrich_quests(rows: list[dict]) -> list[dict]:
    """Attach display metadata from the active gamification catalog."""
    enriched = []
    for row in rows:
        catalog = _QUEST_BY_ID.get(row.get("quest_id", ""), {})
        enriched.append({
            **row,
            "title": catalog.get("title", ""),
            "description": catalog.get("description", ""),
            "quest_type": catalog.get("quest_type", ""),
            "conditions": catalog.get("conditions", {}),
            "rewards": catalog.get("rewards", []),
        })
    return enriched


def _level_progress(profile: dict) -> dict:
    """Build level progress block for the profile response."""
    current_level = int(profile.get("level") or 1)
    won_prizm = float(profile.get("total_won_prizm") or 0)
    _LEVEL_MAP = {row["level"]: row for row in _GAMIFICATION_LEVELS}
    current_info = _LEVEL_MAP.get(current_level, _GAMIFICATION_LEVELS[0])
    next_info = _LEVEL_MAP.get(current_level + 1)
    if next_info:
        span = max(next_info["turnover"] - current_info["turnover"], 1)
        progress_pct = int(min(100, max(0, (won_prizm - current_info["turnover"]) / span * 100)))
        remaining = round(max(next_info["turnover"] - won_prizm, 0), 2)
    else:
        progress_pct = 100
        remaining = 0.0
    return {
        "current_level": current_level,
        "level_name": profile.get("level_name", current_info["name"]),
        "total_won_prizm": round(won_prizm, 2),
        "next_level": current_level + 1 if next_info else None,
        "next_level_name": next_info["name"] if next_info else None,
        "next_level_turnover": next_info["turnover"] if next_info else None,
        "remaining_prizm": remaining,
        "progress_percent": progress_pct,
    }


# ── GET /api/player/{wallet} ───────────────────────────────────────────────────

def _gamification_features(wallet_verified: bool = False) -> dict:
    public_mutations_configured = bool(config.GAMIFICATION_PUBLIC_MUTATIONS_ENABLED)
    public_mutations = bool(public_mutations_configured and wallet_verified)
    return {
        "gamification_public_mutations": public_mutations,
        "gamification_public_mutations_configured": public_mutations_configured,
        "wallet_verification_required": True,
        "wallet_verified": bool(wallet_verified),
        "roulette_enabled": public_mutations,
        "raffle_entry_enabled": public_mutations,
    }


async def player_profile(request: web.Request) -> web.Response:
    """Full player profile: level, bonuses, active quests, roulette spins."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)

    try:
        # Profile (create on first visit)
        from backend.bot.gamification import _get_or_create_profile
        profile = await _get_or_create_profile(wallet)
        if not profile:
            return _json_response({"error": "Failed to load player profile"}, status=500)

        # Active bonuses (not burned, not expired)
        now_iso = datetime.now(timezone.utc).isoformat()
        bonuses = (
            db.client.table("player_bonuses")
            .select("*")
            .eq("wallet", wallet)
            .is_("burned_at", "null")
            .gt("expires_at", now_iso)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
        ) or []

        # Quests: current level + next level only (Rule 5)
        current_level = int(profile.get("level") or 1)
        visible_levels = [current_level, current_level + 1]
        quests = (
            db.client.table("player_quests")
            .select("*")
            .eq("wallet", wallet)
            .in_("level_unlocked", visible_levels)
            .order("level_unlocked", desc=False)
            .execute()
            .data
        ) or []

        wallet_verification = await _wallet_verification_payload(wallet)
        wallet_verified = bool(wallet_verification.get("verified"))

        return _json_response({
            "ok": True,
            "wallet": wallet,
            "profile": {
                **profile,
                "level_progress": _level_progress(profile),
            },
            "bonuses": bonuses,
            "quests": _enrich_quests(quests),
            "features": _gamification_features(wallet_verified),
            "wallet_verification": wallet_verification,
        })

    except Exception:
        logger.exception("API handler failed")
        return _json_response({"error": "Internal error"}, status=500)


# ── GET /api/player/{wallet}/quests ───────────────────────────────────────────

async def player_quests(request: web.Request) -> web.Response:
    """All quest rows with progress for a wallet."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)

    try:
        level_filter = request.query.get("level")
        query = (
            db.client.table("player_quests")
            .select("*")
            .eq("wallet", wallet)
            .order("level_unlocked", desc=False)
        )
        if level_filter:
            try:
                query = query.eq("level_unlocked", int(level_filter))
            except ValueError:
                pass
        quests = query.limit(100).execute().data or []

        return _json_response({
            "ok": True,
            "wallet": wallet,
            "quests": _enrich_quests(quests),
        })
    except Exception:
        logger.exception("API handler failed")
        return _json_response({"error": "Internal error"}, status=500)


# ── POST /api/player/{wallet}/roulette ────────────────────────────────────────

_roulette_limiter = _RateLimiter(max_requests=20, window_seconds=60)


async def player_roulette(request: web.Request) -> web.Response:
    """Spend roulette spins and receive prizes."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)
    if not config.GAMIFICATION_PUBLIC_MUTATIONS_ENABLED:
        return _json_response({"error": "Public gamification mutations require wallet ownership verification"}, status=403)
    if not await _wallet_is_verified(wallet):
        return _json_response({"error": "Wallet ownership verification required"}, status=403)

    ip = client_ip(request)
    if not _roulette_limiter.is_allowed(f"{ip}:{wallet}"):
        return _json_response({"error": "Too many requests, try again later"}, status=429)

    try:
        body = await request.json()
    except Exception:
        body = {}

    spins = max(1, min(int(body.get("spins") or 1), 5))  # cap blast radius until wallet proof exists

    prizes = await _gamification_spin_roulette(wallet, spins)
    if not prizes and spins > 0:
        # Could mean not enough spins
        profile_rows = (
            db.client.table("player_profiles")
            .select("roulette_spins")
            .eq("wallet", wallet)
            .limit(1)
            .execute()
            .data
        )
        available = int(profile_rows[0].get("roulette_spins") or 0) if profile_rows else 0
        if available < spins:
            return _json_response({
                "error": "Not enough roulette spins",
                "available": available,
                "requested": spins,
            }, status=400)

    return _json_response({
        "ok": True,
        "wallet": wallet,
        "spins_used": spins,
        "prizes": prizes,
    })


# ── GET /api/leaderboard/weekly ───────────────────────────────────────────────

async def weekly_leaderboard(request: web.Request) -> web.Response:
    """Top-10 players by won_prizm for the current week."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    try:
        now = datetime.now(timezone.utc)
        # ISO week: Monday = start of week
        week_start = (now - timedelta(days=now.weekday())).date()
        week_end   = (week_start + timedelta(days=6))

        # Try pre-computed leaderboard first
        rows = (
            db.client.table("weekly_leaderboard")
            .select("wallet,rank,won_prizm,prize_distributed")
            .eq("week_start", week_start.isoformat())
            .order("rank", desc=False)
            .limit(10)
            .execute()
            .data
        ) or []

        if not rows:
            # Live computation from bets table for current week
            week_start_iso = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
            week_end_iso   = datetime.combine(week_end,   datetime.max.time()).replace(tzinfo=timezone.utc).isoformat()

            paid_bets = (
                db.client.table("bets")
                .select("sender_wallet,payout_amount,amount_prizm,odds_fixed,reject_reason")
                .in_("status", ["won", "paid"])
                .gte("created_at", week_start_iso)
                .lte("created_at", week_end_iso)
                .limit(5000)
                .execute()
                .data
            ) or []

            totals: dict[str, float] = {}
            for bet in paid_bets:
                if str(bet.get("reject_reason") or "").strip().upper() == "CASHBACK_BONUS":
                    continue
                w = str(bet.get("sender_wallet") or "").strip().upper()
                if not w:
                    continue
                payout = float(bet.get("payout_amount") or 0) or round(
                    float(bet.get("amount_prizm") or 0) * float(bet.get("odds_fixed") or 0), 2
                )
                totals[w] = round(totals.get(w, 0.0) + payout, 2)

            sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
            rows = [
                {"wallet": w, "rank": i + 1, "won_prizm": v, "prize_distributed": False}
                for i, (w, v) in enumerate(sorted_totals[:10])
            ]

        return _json_response({
            "ok": True,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "leaderboard": rows,
        })

    except Exception:
        logger.exception("API handler failed")
        return _json_response({"error": "Internal error"}, status=500)


# ── POST /api/admin/leaderboard/weekly/finalize ───────────────────────────────

async def admin_finalize_weekly_leaderboard(request: web.Request) -> web.Response:
    """Persist weekly leaderboard and distribute top-3 prizes once."""
    context, error = await _require_owner(request)
    if error:
        return error
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    try:
        body = await request.json()
    except Exception:
        body = {}

    week_start = str(body.get("week_start") or request.query.get("week_start") or "").strip() or None
    result = await _gamification_finalize_weekly(week_start=week_start)
    if not result.get("ok"):
        return _json_response({"error": result.get("error") or "Failed to finalize leaderboard"}, status=500)

    await _log_admin_access_event(
        "weekly_leaderboard_finalized",
        actor=context["actor"],
        extra={
            "week_start": result.get("week_start"),
            "week_end": result.get("week_end"),
            "rows": len(result.get("leaderboard") or []),
        },
    )
    return _json_response(result)


# ── POST /api/admin/player/{wallet}/game-session ──────────────────────────────

async def admin_credit_game_session(request: web.Request) -> web.Response:
    """Owner-only manual source for the ИГРОМАН quest until game tracking exists."""
    context, error = await _require_owner(request)
    if error:
        return error
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = _normalize_wallet(request.match_info.get("wallet"))
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)

    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        sessions = max(1, min(int(body.get("sessions") or 1), 24))
    except Exception:
        sessions = 1
    note = str(body.get("note") or "").strip()[:200]

    try:
        await _gamification_increment_quest(wallet, "manual_gameplay", delta=float(sessions))
        await _log_admin_access_event(
            "game_session_credited",
            actor=context["actor"],
            extra={"wallet": wallet, "sessions": sessions, "note": note},
        )
        return _json_response({
            "ok": True,
            "wallet": wallet,
            "sessions": sessions,
        })
    except Exception:
        logger.exception("API handler failed")
        return _json_response({"error": "Internal error"}, status=500)


# ── Admin raffles ─────────────────────────────────────────────────────────────

def _validate_raffle_questions(questions: Any) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(questions, list):
        return [], "questions must be a list"
    if len(questions) != 11:
        return [], "raffle requires exactly 11 questions"

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            return [], f"question {idx} must be an object"
        text = str(item.get("text") or "").strip()
        options = item.get("options") or []
        correct = item.get("correct")
        if not text:
            return [], f"question {idx} text is required"
        if not isinstance(options, list) or len(options) < 2:
            return [], f"question {idx} requires at least 2 options"
        normalized_options = [str(option or "").strip() for option in options]
        if any(not option for option in normalized_options):
            return [], f"question {idx} has empty option"
        if correct is None:
            return [], f"question {idx} correct answer is required"
        normalized.append({
            "id": str(item.get("id") or idx),
            "text": text,
            "options": normalized_options,
            "correct": correct,
        })
    return normalized, None


async def admin_raffles(request: web.Request) -> web.Response:
    context, error = await _require_owner(request)
    if error:
        return error
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    if request.method == "GET":
        rows = (
            db.client.table("raffles")
            .select("id,title,questions,starts_at,ends_at,status,created_at")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
        ) or []
        return _json_response({"ok": True, "raffles": rows})

    try:
        body = await request.json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status=400)

    title = str(body.get("title") or "").strip()
    if not title:
        return _json_response({"error": "title is required"}, status=400)

    questions, questions_error = _validate_raffle_questions(body.get("questions"))
    if questions_error:
        return _json_response({"error": questions_error}, status=400)

    status = str(body.get("status") or "draft").strip().lower()
    if status not in {"draft", "active", "completed", "cancelled"}:
        return _json_response({"error": "invalid raffle status"}, status=400)

    payload = {
        "title": title,
        "questions": questions,
        "starts_at": body.get("starts_at"),
        "ends_at": body.get("ends_at"),
        "status": status,
    }
    row = db.client.table("raffles").insert(payload).execute().data
    await _log_admin_access_event(
        "raffle_created",
        actor=context["actor"],
        extra={"title": title, "status": status, "questions": len(questions)},
    )
    return _json_response({"ok": True, "raffle": row[0] if row else None})


# ── GET /api/raffles/active ───────────────────────────────────────────────────

async def raffles_active(request: web.Request) -> web.Response:
    """Return the currently active raffle (if any)."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = (
            db.client.table("raffles")
            .select("id,title,questions,starts_at,ends_at,status")
            .eq("status", "active")
            .lte("starts_at", now_iso)
            .gte("ends_at", now_iso)
            .order("starts_at", desc=True)
            .limit(1)
            .execute()
            .data
        ) or []

        raffle = rows[0] if rows else None

        # Strip correct answers from questions before serving
        if raffle and raffle.get("questions"):
            safe_questions = []
            for q in (raffle["questions"] or []):
                safe_questions.append({
                    "id":      q.get("id"),
                    "text":    q.get("text"),
                    "options": q.get("options", []),
                })
            raffle["questions"] = safe_questions

        return _json_response({
            "ok": True,
            "raffle": raffle,
            "features": _gamification_features(),
        })

    except Exception:
        logger.exception("API handler failed")
        return _json_response({"error": "Internal error"}, status=500)


# ── POST /api/raffles/{id}/enter ──────────────────────────────────────────────

_raffle_limiter = _RateLimiter(max_requests=5, window_seconds=60)


async def raffle_enter(request: web.Request) -> web.Response:
    """Submit answers to a raffle. Requires a raffle_token."""
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    ip = client_ip(request)
    if not _raffle_limiter.is_allowed(ip):
        return _json_response({"error": "Too many requests, try again later"}, status=429)

    raffle_id_str = str(request.match_info.get("raffle_id") or "").strip()
    if not raffle_id_str.isdigit():
        return _json_response({"error": "raffle_id must be an integer"}, status=400)
    raffle_id = int(raffle_id_str)

    try:
        body = await request.json()
    except Exception:
        return _json_response({"error": "Invalid JSON body"}, status=400)

    wallet = _normalize_wallet(body.get("wallet"))
    answers = body.get("answers") or []
    if not wallet:
        return _json_response({"error": "wallet is required or invalid"}, status=400)
    if not config.GAMIFICATION_PUBLIC_MUTATIONS_ENABLED:
        return _json_response({"error": "Public gamification mutations require wallet ownership verification"}, status=403)
    if not await _wallet_is_verified(wallet):
        return _json_response({"error": "Wallet ownership verification required"}, status=403)
    if not isinstance(answers, list):
        return _json_response({"error": "answers must be a list"}, status=400)

    try:
        result = db.client.rpc("enter_raffle_with_token", {
            "p_raffle_id": raffle_id,
            "p_wallet": wallet,
            "p_answers": answers,
        }).execute().data
        if isinstance(result, list):
            result = result[0] if result else {}
        if not isinstance(result, dict):
            result = {}

        if not result.get("ok"):
            status = int(result.get("status") or 500)
            return _json_response({"error": result.get("error") or "Failed to enter raffle"}, status=status)

        # Increment raffle quest progress
        await _gamification_increment_quest(wallet, "raffle", delta=1.0)

        return _json_response(result)

    except Exception:
        logger.exception("API handler failed")
        return _json_response({"error": "Internal error"}, status=500)


def create_app() -> web.Application:
    app = web.Application(
        middlewares=[cors_middleware],
        client_max_size=max(int(config.API_MAX_REQUEST_BYTES or 0), 16_384),
    )
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
    app.router.add_get("/api/wallets/{wallet}/verification", wallet_verification_status)
    app.router.add_post("/api/wallets/{wallet}/verification/challenge", wallet_verification_challenge)
    app.router.add_get("/api/admin/feed", operator_feed)
    app.router.add_get("/api/admin/audit-log", operator_audit_log)
    app.router.add_post("/api/admin/bets/{tx_id}/settle", manual_settle_bet)
    app.router.add_post("/api/admin/bets/{tx_id}/mark-paid", mark_bet_paid)
    app.router.add_get("/api/admin/wallet", admin_wallet_info)
    app.router.add_get("/api/admin/wallet/status", admin_wallet_status)
    app.router.add_post("/api/admin/wallet/emergency-stop", admin_wallet_emergency_stop)
    app.router.add_post("/api/admin/wallet/resume", admin_wallet_resume)
    app.router.add_post("/api/admin/wallet/passphrase", admin_wallet_set_passphrase)
    app.router.add_get("/api/admin/export-csv", export_bets_csv)

    # ── Gamification ─────────────────────────────────────────────────────────
    app.router.add_get("/api/player/{wallet}",          player_profile)
    app.router.add_get("/api/player/{wallet}/quests",   player_quests)
    app.router.add_post("/api/player/{wallet}/roulette", player_roulette)
    app.router.add_get("/api/leaderboard/weekly",        weekly_leaderboard)
    app.router.add_post("/api/admin/leaderboard/weekly/finalize", admin_finalize_weekly_leaderboard)
    app.router.add_post("/api/admin/player/{wallet}/game-session", admin_credit_game_session)
    app.router.add_get("/api/admin/raffles",             admin_raffles)
    app.router.add_post("/api/admin/raffles",            admin_raffles)
    app.router.add_get("/api/raffles/active",            raffles_active)
    app.router.add_post("/api/raffles/{raffle_id}/enter", raffle_enter)

    # Serve frontend static files
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if frontend_dir.is_dir():
        async def _root_index(_req):
            return web.FileResponse(frontend_dir / "index.html")
        app.router.add_get("/", _root_index)
        app.router.add_static("/", frontend_dir, show_index=False)

    return app


if __name__ == "__main__":
    db.init()
    web.run_app(
        create_app(),
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8081")),
    )
