# -*- coding: utf-8 -*-
"""Admin authentication helpers for the operator console."""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import web

from backend.config import config

ALLOWED_ADMIN_ROLES = {"super_admin", "operator", "finance", "viewer"}


def normalize_login(login: str) -> str:
    return re.sub(r"[^a-z0-9._-]", "", str(login or "").strip().lower())


def validate_login(login: str) -> bool:
    normalized = normalize_login(login)
    return 3 <= len(normalized) <= 32 and normalized == str(login or "").strip().lower()


def validate_password(password: str) -> bool:
    return len(str(password or "")) >= 8


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def validate_email(email: str) -> bool:
    normalized = normalize_email(email)
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized))


def normalize_role(role: str, *, allow_super_admin: bool = False) -> str:
    value = str(role or "operator").strip().lower()
    if value == "super_admin" and allow_super_admin:
        return value
    if value in {"operator", "finance", "viewer"}:
        return value
    return "operator"


def hash_password(password: str) -> str:
    iterations = max(int(config.ADMIN_PASSWORD_ITERATIONS or 0), 120000)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, raw_iterations, salt_hex, digest_hex = str(stored_hash or "").split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(current, expected)
    except Exception:
        return False


def issue_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def session_expires_at() -> str:
    lifetime_hours = max(int(config.ADMIN_SESSION_HOURS or 0), 1)
    return (datetime.now(timezone.utc) + timedelta(hours=lifetime_hours)).isoformat()


def client_ip(request: web.Request) -> str:
    forwarded = str(request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return str(request.remote or "")


def serialize_admin_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "id": user.get("id"),
        "login": user.get("login"),
        "email": user.get("email"),
        "role": user.get("role"),
        "is_active": bool(user.get("is_active", True)),
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
    }


def role_can_manage_users(role: str) -> bool:
    return str(role or "").strip().lower() == "super_admin"


def role_can_mark_paid(role: str) -> bool:
    return str(role or "").strip().lower() in {"super_admin", "finance"}
