# -*- coding: utf-8 -*-
"""Bet Intent API (Hash-Coupon + Prototype Dashboard)."""
import json
import random
import string
from pathlib import Path
from datetime import datetime, timezone, timedelta
from aiohttp import web

from backend.db.supabase_client import db


OUTCOME_MAP = {
    "П1": "p1",
    "P1": "p1",
    "1": "p1",
    "X": "x",
    "П2": "p2",
    "P2": "p2",
    "2": "p2",
    "1X": "p1x",
    "12": "p12",
    "X2": "px2",
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _with_cors(response: web.StreamResponse) -> web.StreamResponse:
    response.headers.update(CORS_HEADERS)
    return response


def _json_response(payload: dict, status: int = 200) -> web.Response:
    return _with_cors(web.json_response(payload, status=status))


def _load_matches_cache() -> dict:
    p = Path(__file__).resolve().parents[2] / "frontend" / "matches.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(m.get("id")): m for m in data.get("matches", []) if m.get("id")}


def _extract_odds(match: dict, outcome: str):
    key = OUTCOME_MAP.get(outcome)
    if not key:
        return None
    val = match.get(key)
    if not val or val in ("—", "-", "0", "0.00"):
        return None
    try:
        return round(float(val), 2)
    except Exception:
        return None


def _intent_hash(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _rank_preview(turnover: float, accepted_count: int) -> dict:
    tiers = [
        ("Observer", 0),
        ("Runner", 1500),
        ("Operator", 5000),
        ("Strategist", 15000),
        ("Imperator", 50000),
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


async def _ensure_db_ready():
    if not db.initialized:
        db.init()
    return db.initialized


async def create_intent(request: web.Request):
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    payload = await request.json()
    match_id = str(payload.get("match_id", "")).strip()
    outcome = str(payload.get("outcome", "")).strip().upper()
    sender_wallet = str(payload.get("sender_wallet", "")).strip().upper()

    if not match_id or not outcome or not sender_wallet:
        return _json_response({"error": "match_id, outcome, sender_wallet are required"}, status=400)

    matches = _load_matches_cache()
    match = matches.get(match_id)
    if not match:
        return _json_response({"error": "match not found in current cache"}, status=404)

    odds = _extract_odds(match, outcome)
    if not odds:
        return _json_response({"error": "outcome/odds unavailable"}, status=400)

    intent = None
    for _ in range(10):
        h = _intent_hash(6)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        try:
            await db.create_bet_intent(
                intent_hash=h,
                match_id=match_id,
                sender_wallet=sender_wallet,
                outcome=outcome,
                odds_fixed=odds,
                expires_at=expires_at,
            )
            intent = {
                "intent_hash": h,
                "odds_fixed": odds,
                "expires_at": expires_at,
                "match_id": match_id,
                "sender_wallet": sender_wallet,
            }
            break
        except Exception:
            continue

    if not intent:
        return _json_response({"error": "failed to create intent"}, status=500)

    return _json_response(intent)


async def get_intent_status(request: web.Request):
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    intent_hash = str(request.match_info.get("intent_hash", "")).strip().upper()
    if not intent_hash:
        return _json_response({"error": "intent_hash is required"}, status=400)

    intent = await db.get_bet_intent(intent_hash)
    if not intent:
        return _json_response({"error": "intent not found"}, status=404)

    bet_rows = db.client.table("bets").select("*").eq("intent_hash", intent_hash).order("created_at", desc=True).limit(1).execute().data
    bet = bet_rows[0] if bet_rows else None
    expires_at = _parse_dt(intent.get("expires_at"))
    now = datetime.now(timezone.utc)

    if bet:
        status = bet.get("status", "accepted")
    elif expires_at and expires_at < now:
        status = "expired"
    else:
        status = "awaiting_payment"

    return _json_response({
        "status": status,
        "intent": intent,
        "bet": bet,
    })


async def wallet_dashboard(request: web.Request):
    if not await _ensure_db_ready():
        return _json_response({"error": "Database not configured"}, status=500)

    wallet = str(request.match_info.get("wallet", "")).strip().upper()
    if not wallet:
        return _json_response({"error": "wallet is required"}, status=400)

    intents = db.client.table("bet_intents").select("*").eq("sender_wallet", wallet).order("created_at", desc=True).limit(10).execute().data
    bets = db.client.table("bets").select("*").eq("sender_wallet", wallet).order("created_at", desc=True).limit(25).execute().data

    now = datetime.now(timezone.utc)
    bet_by_intent = {str(b.get("intent_hash")): b for b in bets if b.get("intent_hash")}
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
    accepted_statuses = {"accepted", "won", "lost", "paid", "refunded", "refund_pending"}
    counts = {
        "accepted": 0,
        "rejected": 0,
        "won": 0,
        "lost": 0,
        "refund_pending": 0,
        "paid": 0,
    }
    for bet in bets:
        status = str(bet.get("status", "")).lower()
        amount = float(bet.get("amount_prizm") or 0)
        odds_fixed = float(bet.get("odds_fixed") or 0)
        if status in accepted_statuses:
            turnover += amount
            potential_payout += amount * odds_fixed
        if status in counts:
            counts[status] += 1

    rank = _rank_preview(turnover, counts["accepted"] + counts["won"] + counts["lost"] + counts["paid"])

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


async def health(_: web.Request):
    return _json_response({"ok": True})


async def options_preflight(_: web.Request):
    return _with_cors(web.Response(status=204))


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_route("OPTIONS", "/{tail:.*}", options_preflight)
    app.router.add_get("/health", health)
    app.router.add_post("/api/intents", create_intent)
    app.router.add_get("/api/intents/{intent_hash}", get_intent_status)
    app.router.add_get("/api/wallets/{wallet}/dashboard", wallet_dashboard)
    return app


if __name__ == "__main__":
    db.init()
    web.run_app(create_app(), host="0.0.0.0", port=8081)