#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gamification engine for PrizmBet v3.

Entry points
------------
- on_bet_settled()  — call from v3_settler.py after update_bet_settlement()
- check_level_up()  — called internally; also available for manual/admin use
- spin_roulette()   — POST /api/player/{wallet}/roulette

All writes use the service_role Supabase client (RLS bypassed).
"""
from __future__ import annotations

import logging
import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.db.supabase_client import db

log = logging.getLogger(__name__)

# ── Level table (from CODEX) ───────────────────────────────────────────────────

LEVELS: list[dict] = [
    {"level": 1,  "name": "НАБЛЮДАТЕЛЬ",        "turnover": 0,                    "quests_required": 0},
    {"level": 2,  "name": "НАЧИНАЮЩИЙ ИГРОК",   "turnover": 1_500,                "quests_required": 1},
    {"level": 3,  "name": "ИГРОК",              "turnover": 100_000,              "quests_required": 2},
    {"level": 4,  "name": "ОПЫТНЫЙ ИГРОК",      "turnover": 1_000_000,            "quests_required": 3},
    {"level": 5,  "name": "ИГРАЮЩИЙ ТРЕНЕР",    "turnover": 10_000_000,           "quests_required": 4},
    {"level": 6,  "name": "НАЧИНАЮЩИЙ ТРЕНЕР",  "turnover": 50_000_000,           "quests_required": 5},
    {"level": 7,  "name": "ТРЕНЕР",             "turnover": 100_000_000,          "quests_required": 6},
    {"level": 8,  "name": "ОПЫТНЫЙ ТРЕНЕР",     "turnover": 250_000_000,          "quests_required": 7},
    {"level": 9,  "name": "СТАРШИЙ ТРЕНЕР",     "turnover": 500_000_000,          "quests_required": 8},
    {"level": 10, "name": "СОВЕТНИК",           "turnover": 1_000_000_000,        "quests_required": 9},
    {"level": 11, "name": "ХРАНИТЕЛЬ ТРАДИЦИЙ", "turnover": 2_000_000_000,        "quests_required": 0},
]

MAX_LEVEL = LEVELS[-1]["level"]
_LEVEL_MAP: dict[int, dict] = {row["level"]: row for row in LEVELS}


def _level_info(level: int) -> dict:
    return _LEVEL_MAP.get(level, LEVELS[0])


# ── Quest catalog ──────────────────────────────────────────────────────────────
# quest_type values:
#   "bets_count"  — increments by 1 on every settled bet
#   "won_prizm"   — increments by won_amount when won
#   "single_win"  — progress = max(progress, single_win); completes when a
#                   single bet win >= target
#   "roulette"    — incremented from spin_roulette()
#   "raffle"      — incremented from raffle entry endpoint
#   "top3"        — incremented from weekly leaderboard finalization
#   "bonus_used"  — incremented when player activates a bonus

QUEST_CATALOG: list[dict] = [
    # ── Level 1 ──────────────────────────────────────────────────────────────
    {"quest_id": "l1_first_bet",      "level_unlocked": 1,  "target": 1.0,              "times_required": 1, "quest_type": "bets_count",  "description": "Сделать первую ставку"},
    # ── Level 2 ──────────────────────────────────────────────────────────────
    {"quest_id": "l2_win_1500",       "level_unlocked": 2,  "target": 1_500.0,          "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 1 500 PRIZM"},
    # ── Level 3 ──────────────────────────────────────────────────────────────
    {"quest_id": "l3_win_50k",        "level_unlocked": 3,  "target": 50_000.0,         "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 50 000 PRIZM"},
    # ── Level 4 (2 quests) ───────────────────────────────────────────────────
    {"quest_id": "l4_win_500k",       "level_unlocked": 4,  "target": 500_000.0,        "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 500 000 PRIZM"},
    {"quest_id": "l4_bets_50",        "level_unlocked": 4,  "target": 50.0,             "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 50 ставок"},
    # ── Level 5 (3 quests) ───────────────────────────────────────────────────
    {"quest_id": "l5_win_5m",         "level_unlocked": 5,  "target": 5_000_000.0,      "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 5 000 000 PRIZM"},
    {"quest_id": "l5_bets_200",       "level_unlocked": 5,  "target": 200.0,            "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 200 ставок"},
    {"quest_id": "l5_roulette_10",    "level_unlocked": 5,  "target": 10.0,             "times_required": 1, "quest_type": "roulette",    "description": "Прокрутить рулетку 10 раз"},
    # ── Level 6 (4 quests) ───────────────────────────────────────────────────
    {"quest_id": "l6_win_50m",        "level_unlocked": 6,  "target": 50_000_000.0,     "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 50 000 000 PRIZM"},
    {"quest_id": "l6_bets_500",       "level_unlocked": 6,  "target": 500.0,            "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 500 ставок"},
    {"quest_id": "l6_raffle_entry",   "level_unlocked": 6,  "target": 1.0,              "times_required": 1, "quest_type": "raffle",      "description": "Участвовать в розыгрыше"},
    {"quest_id": "l6_single_win_100k","level_unlocked": 6,  "target": 100_000.0,        "times_required": 1, "quest_type": "single_win",  "description": "Выиграть 100 000 PRIZM в одной ставке"},
    # ── Level 7 (5 quests) ───────────────────────────────────────────────────
    {"quest_id": "l7_win_100m",       "level_unlocked": 7,  "target": 100_000_000.0,    "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 100 000 000 PRIZM"},
    {"quest_id": "l7_bets_1000",      "level_unlocked": 7,  "target": 1_000.0,          "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 1 000 ставок"},
    {"quest_id": "l7_roulette_50",    "level_unlocked": 7,  "target": 50.0,             "times_required": 1, "quest_type": "roulette",    "description": "Прокрутить рулетку 50 раз"},
    {"quest_id": "l7_raffle_3",       "level_unlocked": 7,  "target": 3.0,              "times_required": 1, "quest_type": "raffle",      "description": "Участвовать в 3 розыгрышах"},
    {"quest_id": "l7_single_win_1m",  "level_unlocked": 7,  "target": 1_000_000.0,      "times_required": 1, "quest_type": "single_win",  "description": "Выиграть 1 000 000 PRIZM в одной ставке"},
    # ── Level 8 (6 quests) ───────────────────────────────────────────────────
    {"quest_id": "l8_win_250m",       "level_unlocked": 8,  "target": 250_000_000.0,    "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 250 000 000 PRIZM"},
    {"quest_id": "l8_bets_5000",      "level_unlocked": 8,  "target": 5_000.0,          "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 5 000 ставок"},
    {"quest_id": "l8_roulette_200",   "level_unlocked": 8,  "target": 200.0,            "times_required": 1, "quest_type": "roulette",    "description": "Прокрутить рулетку 200 раз"},
    {"quest_id": "l8_raffle_10",      "level_unlocked": 8,  "target": 10.0,             "times_required": 1, "quest_type": "raffle",      "description": "Участвовать в 10 розыгрышах"},
    {"quest_id": "l8_top3",           "level_unlocked": 8,  "target": 1.0,              "times_required": 1, "quest_type": "top3",        "description": "Попасть в топ-3 недели"},
    {"quest_id": "l8_single_win_10m", "level_unlocked": 8,  "target": 10_000_000.0,     "times_required": 1, "quest_type": "single_win",  "description": "Выиграть 10 000 000 PRIZM в одной ставке"},
    # ── Level 9 (7 quests) ───────────────────────────────────────────────────
    {"quest_id": "l9_win_500m",       "level_unlocked": 9,  "target": 500_000_000.0,    "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 500 000 000 PRIZM"},
    {"quest_id": "l9_bets_20k",       "level_unlocked": 9,  "target": 20_000.0,         "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 20 000 ставок"},
    {"quest_id": "l9_roulette_1000",  "level_unlocked": 9,  "target": 1_000.0,          "times_required": 1, "quest_type": "roulette",    "description": "Прокрутить рулетку 1 000 раз"},
    {"quest_id": "l9_raffle_30",      "level_unlocked": 9,  "target": 30.0,             "times_required": 1, "quest_type": "raffle",      "description": "Участвовать в 30 розыгрышах"},
    {"quest_id": "l9_top3_3",         "level_unlocked": 9,  "target": 3.0,              "times_required": 1, "quest_type": "top3",        "description": "Трижды попасть в топ-3 недели"},
    {"quest_id": "l9_single_win_100m","level_unlocked": 9,  "target": 100_000_000.0,    "times_required": 1, "quest_type": "single_win",  "description": "Выиграть 100 000 000 PRIZM в одной ставке"},
    {"quest_id": "l9_bonus_used_5",   "level_unlocked": 9,  "target": 5.0,              "times_required": 1, "quest_type": "bonus_used",  "description": "Активировать бонус 5 раз"},
    # ── Level 10 (8 quests) ──────────────────────────────────────────────────
    {"quest_id": "l10_win_1b",        "level_unlocked": 10, "target": 1_000_000_000.0,  "times_required": 1, "quest_type": "won_prizm",   "description": "Выиграть 1 000 000 000 PRIZM"},
    {"quest_id": "l10_bets_100k",     "level_unlocked": 10, "target": 100_000.0,        "times_required": 1, "quest_type": "bets_count",  "description": "Сделать 100 000 ставок"},
    {"quest_id": "l10_roulette_5k",   "level_unlocked": 10, "target": 5_000.0,          "times_required": 1, "quest_type": "roulette",    "description": "Прокрутить рулетку 5 000 раз"},
    {"quest_id": "l10_raffle_100",    "level_unlocked": 10, "target": 100.0,            "times_required": 1, "quest_type": "raffle",      "description": "Участвовать в 100 розыгрышах"},
    {"quest_id": "l10_top3_10",       "level_unlocked": 10, "target": 10.0,             "times_required": 1, "quest_type": "top3",        "description": "10 раз попасть в топ-3 недели"},
    {"quest_id": "l10_single_win_1b", "level_unlocked": 10, "target": 1_000_000_000.0,  "times_required": 1, "quest_type": "single_win",  "description": "Выиграть 1 000 000 000 PRIZM в одной ставке"},
    {"quest_id": "l10_bonus_used_20", "level_unlocked": 10, "target": 20.0,             "times_required": 1, "quest_type": "bonus_used",  "description": "Активировать бонус 20 раз"},
    {"quest_id": "l10_prizmaster",    "level_unlocked": 10, "target": 1.0,              "times_required": 1, "quest_type": "prizmaster",  "description": "Получить значок НАСТОЯЩЕГО ПРИЗМАЧА"},
]

# Document-backed quest catalog. The earlier table is kept as historical
# fallback text; this assignment is the active runtime catalog.
_RUSSIAN_FOOTBALL_CONDITIONS = {
    "min_amount": 5_000,
    "min_odds": 1.5,
    "league_keywords": ("russia", "russian", "росси", "рпл", "премьер", "фнл"),
    "sport_keywords": ("football", "soccer", "футбол"),
}


def _reward_spins(value: int) -> dict[str, Any]:
    return {"type": "roulette_spins", "value": int(value)}


def _reward_token(value: int = 1) -> dict[str, Any]:
    return {"type": "raffle_token", "value": int(value)}


def _reward_badge(badge: str) -> dict[str, Any]:
    return {"type": "badge", "badge": badge}


def _reward_bonus(
    bonus_key: str,
    bonus_type: str,
    value: float,
    *,
    expires_days: int,
    burn_on_level_up: bool,
) -> dict[str, Any]:
    return {
        "type": "bonus",
        "bonus_key": bonus_key,
        "bonus_type": bonus_type,
        "value": value,
        "expires_days": expires_days,
        "burn_on_level_up": burn_on_level_up,
    }


def _quest(
    level: int,
    slug: str,
    title: str,
    description: str,
    quest_type: str,
    target: float,
    *,
    conditions: dict[str, Any] | None = None,
    rewards: list[dict[str, Any]] | None = None,
    times_required: int = 1,
) -> dict[str, Any]:
    return {
        "quest_id": f"l{level}_{slug}",
        "level_unlocked": level,
        "title": title,
        "description": description,
        "quest_type": quest_type,
        "target": float(target),
        "times_required": int(times_required),
        "conditions": conditions or {},
        "rewards": rewards or [],
    }


def _level_quests(level: int) -> list[dict[str, Any]]:
    gamer_rewards = (
        [_reward_bonus("freespins_1500", "freespins", 1_500, expires_days=30, burn_on_level_up=False)]
        if level <= 3
        else [_reward_spins(15)]
    )
    quests = [
        _quest(
            level,
            "football_patriot",
            "ФУТБОЛЬНЫЙ ПАТРИОТ",
            "Сделать 3 выигрышные ставки на чемпионат России: ставка от 5 000 PRIZM, коэффициент от 1.5.",
            "football_patriot",
            3,
            conditions=dict(_RUSSIAN_FOOTBALL_CONDITIONS),
            rewards=[_reward_token(1), _reward_spins(15)],
        ),
        _quest(
            level,
            "gamer",
            "ИГРОМАН",
            "Сыграть 3 игровые сессии по 1 часу. Прогресс начисляется вручную после подключения игрового трекинга.",
            "manual_gameplay",
            3,
            rewards=gamer_rewards,
        ),
    ]

    if level >= 2:
        quests.append(_quest(
            level,
            "prizmaster",
            "НАСТОЯЩИЙ ПРИЗМАЧ",
            "Сделать 10 ставок на аутсайдеров с коэффициентом от 10.",
            "outsider_bets",
            10,
            conditions={"min_odds": 10},
            rewards=[_reward_badge("prizmaster"), _reward_spins(50)],
        ))
    if level >= 3:
        quests.append(_quest(
            level,
            "risky",
            "РИСКОВЫЙ",
            "Набрать 100 000 PRIZM выигранного оборота на ставках с коэффициентом от 3.",
            "outsider_won_prizm",
            100_000,
            conditions={"min_odds": 3},
            rewards=[
                _reward_spins(35),
                _reward_bonus("cashback_20", "cashback", 0.20, expires_days=30, burn_on_level_up=False),
            ],
        ))
    if level >= 4:
        quests.append(_quest(
            level,
            "temp_millionaire",
            "ВРЕМЕННЫЙ МИЛЛИОНЕР",
            "Набрать 1 000 000 PRIZM выигранного оборота.",
            "won_prizm_threshold",
            1_000_000,
            rewards=[
                _reward_spins(35),
                _reward_bonus("temp_millionaire", "pct_win", 0.005, expires_days=7, burn_on_level_up=True),
            ],
        ))
    if level >= 5:
        quests.append(_quest(
            level,
            "millionaire",
            "МИЛЛИОНЕР",
            "Набрать 10 000 000 PRIZM выигранного оборота.",
            "won_prizm_threshold",
            10_000_000,
            rewards=[
                _reward_spins(35),
                _reward_bonus("millionaire_005", "pct_win", 0.005, expires_days=3650, burn_on_level_up=True),
            ],
        ))
    if level >= 6:
        quests.append(_quest(
            level,
            "financier",
            "ФИНАНСИСТ",
            "Набрать 50 000 000 PRIZM выигранного оборота.",
            "won_prizm_threshold",
            50_000_000,
            rewards=[
                _reward_spins(50),
                _reward_bonus("financier_010", "pct_win", 0.010, expires_days=3650, burn_on_level_up=True),
            ],
        ))
    if level >= 7:
        quests.append(_quest(
            level,
            "billionaire",
            "МИЛЛИАРДЕР",
            "Набрать 1 000 000 000 PRIZM выигранного оборота.",
            "won_prizm_threshold",
            1_000_000_000,
            rewards=[
                _reward_spins(100),
                _reward_bonus("billionaire_015", "pct_win", 0.015, expires_days=3650, burn_on_level_up=True),
            ],
        ))
    if level >= 8:
        quests.append(_quest(
            level,
            "magnate",
            "МАГНАТ",
            "Набрать 1 500 000 000 PRIZM выигранного оборота.",
            "won_prizm_threshold",
            1_500_000_000,
            rewards=[
                _reward_spins(200),
                _reward_bonus("magnate_020", "pct_win", 0.020, expires_days=3650, burn_on_level_up=True),
            ],
        ))
    if level >= 9:
        quests.append(_quest(
            level,
            "major",
            "МАЖОР",
            "Набрать 2 000 000 000 PRIZM выигранного оборота.",
            "won_prizm_threshold",
            2_000_000_000,
            rewards=[
                _reward_spins(350),
                _reward_bonus("major_025", "pct_win", 0.025, expires_days=3650, burn_on_level_up=True),
            ],
        ))

    return quests


QUEST_CATALOG = [
    quest
    for _level in range(1, 11)
    for quest in _level_quests(_level)
]

QUEST_CATALOG.extend([
    _quest(
        11,
        "keeper_raffle",
        "ХРАНИТЕЛЬ ВОПРОСОВ",
        "Участвовать в 11 розыгрышах после достижения финального уровня.",
        "raffle",
        11,
        rewards=[_reward_token(1), _reward_spins(50)],
    ),
    _quest(
        11,
        "keeper_top3",
        "ХРАНИТЕЛЬ ПОБЕД",
        "Попасть в топ-3 недельного рейтинга 3 раза после достижения финального уровня.",
        "top3",
        3,
        rewards=[_reward_spins(150)],
    ),
])

QUEST_BY_ID: dict[str, dict] = {q["quest_id"]: q for q in QUEST_CATALOG}

# Sets of quest_ids by type — for fast filtering without DB quest_type column
_QUESTS_BY_TYPE: dict[str, set[str]] = {}
for _q in QUEST_CATALOG:
    _QUESTS_BY_TYPE.setdefault(_q["quest_type"], set()).add(_q["quest_id"])


# ── Roulette prizes ────────────────────────────────────────────────────────────
# Weights sum to 10 000. NOT shown to players — only in /rules page.

_ROULETTE_PRIZES: list[dict] = [
    {"prize_type": "nothing",          "weight": 9869, "prize_value": None},
    {"prize_type": "spins_15",         "weight": 67,   "prize_value": "15"},
    {"prize_type": "cashback_20",      "weight": 33,   "prize_value": "0.20"},
    {"prize_type": "win_boost_50",     "weight": 10,   "prize_value": "0.50"},
    {"prize_type": "temp_millionaire", "weight": 14,   "prize_value": "0.005"},
    {"prize_type": "raffle_token",     "weight": 7,    "prize_value": "1"},
]

_PRIZE_KEYS:    list[str] = [p["prize_type"]  for p in _ROULETTE_PRIZES]
_PRIZE_WEIGHTS: list[int] = [p["weight"]      for p in _ROULETTE_PRIZES]
_PRIZE_MAP:     dict[str, dict] = {p["prize_type"]: p for p in _ROULETTE_PRIZES}
_PRIZE_TOTAL_WEIGHT = sum(_PRIZE_WEIGHTS)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _roll_roulette_prize() -> str:
    ticket = secrets.randbelow(_PRIZE_TOTAL_WEIGHT)
    cursor = 0
    for prize in _ROULETTE_PRIZES:
        cursor += int(prize["weight"])
        if ticket < cursor:
            return str(prize["prize_type"])
    return str(_ROULETTE_PRIZES[-1]["prize_type"])


def _rpc_scalar(data: Any, function_name: str) -> Any:
    if isinstance(data, list):
        if not data:
            return None
        data = data[0]
    if isinstance(data, dict):
        if function_name in data:
            return data[function_name]
        if len(data) == 1:
            return next(iter(data.values()))
    return data


async def _rpc_int(function_name: str, params: dict[str, Any]) -> int | None:
    if not db.initialized:
        return None
    try:
        value = _rpc_scalar(db.client.rpc(function_name, params).execute().data, function_name)
        return int(value)
    except Exception as exc:
        log.error("gamification.%s rpc failed: %s", function_name, exc)
        return None


async def _spend_roulette_spins(wallet: str, spins: int) -> int | None:
    remaining = await _rpc_int(
        "spend_player_roulette_spins",
        {"p_wallet": wallet, "p_spins": int(spins)},
    )
    if remaining is None or remaining < 0:
        return None
    return remaining


async def _add_roulette_spins(wallet: str, delta: int) -> int | None:
    remaining = await _rpc_int(
        "add_player_roulette_spins",
        {"p_wallet": wallet, "p_delta": int(delta)},
    )
    if remaining is None or remaining < 0:
        return None
    return remaining


async def _add_raffle_tokens(wallet: str, delta: int) -> int | None:
    remaining = await _rpc_int(
        "add_player_raffle_tokens",
        {"p_wallet": wallet, "p_delta": int(delta)},
    )
    if remaining is None or remaining < 0:
        return None
    return remaining


# ── Profile helpers ────────────────────────────────────────────────────────────

async def _get_or_create_profile(wallet: str) -> dict | None:
    """Fetch or create a player_profiles row. Returns None on DB error."""
    if not db.initialized:
        return None
    try:
        rows = (
            db.client.table("player_profiles")
            .select("*")
            .eq("wallet", wallet)
            .limit(1)
            .execute()
            .data
        )
        if rows:
            profile = rows[0]
            current_level = int(profile.get("level") or 1)
            await _init_quests_for_level(wallet, current_level)
            if current_level + 1 <= MAX_LEVEL:
                await _init_quests_for_level(wallet, current_level + 1)
            return profile

        # New player — insert and init level-1 quests
        new_row: dict[str, Any] = {
            "wallet": wallet,
            "level": 1,
            "level_name": _level_info(1)["name"],
            "total_won_prizm": 0,
            "total_bet_turnover": 0,
            "roulette_spins": 0,
            "raffle_tokens": 0,
            "prizmaster_badge": False,
        }
        result = db.client.table("player_profiles").insert(new_row).execute().data
        if result:
            await _init_quests_for_level(wallet, 1)
            await _init_quests_for_level(wallet, 2)   # preview next level
            return result[0]
        return None
    except Exception as exc:
        log.error("gamification._get_or_create_profile wallet=%s: %s", wallet[:18], exc)
        return None


async def _init_quests_for_level(wallet: str, level: int) -> None:
    """Insert quest rows for *level* if they don't exist yet (idempotent)."""
    if not db.initialized:
        return
    try:
        existing_rows = (
            db.client.table("player_quests")
            .select("quest_id")
            .eq("wallet", wallet)
            .eq("level_unlocked", level)
            .execute()
            .data
        ) or []
        existing_ids = {str(row.get("quest_id") or "") for row in existing_rows}
    except Exception as exc:
        log.warning("gamification._init_quests existing wallet=%s level=%s: %s", wallet[:18], level, exc)
        existing_ids = set()

    for q in QUEST_CATALOG:
        if q["level_unlocked"] != level:
            continue
        if q["quest_id"] in existing_ids:
            continue
        try:
            db.client.table("player_quests").insert({
                "wallet": wallet,
                "quest_id": q["quest_id"],
                "level_unlocked": q["level_unlocked"],
                "progress": 0,
                "target": q["target"],
                "times_required": q["times_required"],
                "times_completed": 0,
                "completed": False,
                "reward_claimed": False,
            }).execute()
        except Exception as exc:
            err = str(exc).lower()
            if "duplicate" in err or "unique" in err or "23505" in err:
                continue
            log.warning(
                "gamification._init_quests quest=%s wallet=%s: %s",
                q["quest_id"], wallet[:18], exc,
            )


# ── Main entry point ───────────────────────────────────────────────────────────

def _matches_any_keyword(value: str, keywords: tuple[str, ...] | list[str]) -> bool:
    haystack = str(value or "").casefold()
    return any(str(keyword or "").casefold() in haystack for keyword in keywords)


def _is_russian_football_context(league: str, sport: str, conditions: dict[str, Any]) -> bool:
    combined = f"{league or ''} {sport or ''}"
    league_keywords = conditions.get("league_keywords") or ()
    sport_keywords = conditions.get("sport_keywords") or ()
    return (
        _matches_any_keyword(combined, league_keywords)
        and _matches_any_keyword(combined, sport_keywords)
    )


def _quest_progress_delta(
    catalog: dict,
    *,
    amount: float,
    odds: float,
    won: bool,
    won_amount: float,
    single_win: float,
    league: str,
    sport: str,
) -> float | None:
    quest_type = str(catalog.get("quest_type") or "")
    conditions = catalog.get("conditions") or {}

    if quest_type == "bets_count":
        return 1.0
    if quest_type == "won_prizm":
        return won_amount if won_amount > 0 else None
    if quest_type == "single_win":
        target = float(catalog.get("target") or 1)
        return single_win if single_win >= target else None
    if quest_type == "football_patriot":
        if not won:
            return None
        if amount < float(conditions.get("min_amount") or 0):
            return None
        if odds < float(conditions.get("min_odds") or 0):
            return None
        if not _is_russian_football_context(league, sport, conditions):
            return None
        return 1.0
    if quest_type == "outsider_bets":
        return 1.0 if odds >= float(conditions.get("min_odds") or 0) else None
    if quest_type == "outsider_won_prizm":
        if not won or odds < float(conditions.get("min_odds") or 0):
            return None
        return won_amount if won_amount > 0 else None
    if quest_type == "won_prizm_threshold":
        return won_amount if won_amount > 0 else None
    return None


async def _grant_roulette_spins_reward(wallet: str, count: int, source: str) -> None:
    if count <= 0:
        return
    remaining = await _add_roulette_spins(wallet, count)
    if remaining is None:
        log.warning("gamification quest spins failed wallet=%s count=%d", wallet[:18], count)
        return
    try:
        db.client.table("roulette_log").insert({
            "wallet": wallet,
            "event_type": "earned",
            "spins_delta": count,
            "source": source,
        }).execute()
    except Exception as exc:
        log.warning("gamification.quest_roulette_log wallet=%s source=%s: %s", wallet[:18], source, exc)


async def _grant_raffle_tokens_reward(wallet: str, count: int, source: str) -> None:
    if count <= 0:
        return
    remaining = await _add_raffle_tokens(wallet, count)
    if remaining is None:
        log.warning("gamification quest token failed wallet=%s count=%d", wallet[:18], count)
        return
    try:
        db.client.table("raffle_tokens_log").insert({
            "wallet": wallet,
            "delta": count,
            "source": source,
        }).execute()
    except Exception as exc:
        log.warning("gamification.quest_raffle_log wallet=%s source=%s: %s", wallet[:18], source, exc)


async def _grant_quest_rewards(wallet: str, catalog: dict) -> None:
    source = f"quest:{catalog.get('quest_id')}"
    for reward in catalog.get("rewards") or []:
        reward_type = str(reward.get("type") or "")
        try:
            if reward_type == "roulette_spins":
                await _grant_roulette_spins_reward(wallet, int(reward.get("value") or 0), source)
            elif reward_type == "raffle_token":
                await _grant_raffle_tokens_reward(wallet, int(reward.get("value") or 0), source)
            elif reward_type == "bonus":
                await _upsert_bonus(wallet, {
                    "bonus_type": reward["bonus_type"],
                    "bonus_key": reward["bonus_key"],
                    "value": float(reward.get("value") or 0),
                    "expires_at": _expires_iso(int(reward.get("expires_days") or 30)),
                    "burn_on_level_up": bool(reward.get("burn_on_level_up")),
                    "source": source,
                })
            elif reward_type == "badge" and reward.get("badge") == "prizmaster":
                db.client.table("player_profiles").update({
                    "prizmaster_badge": True,
                    "prizmaster_level": int(catalog.get("level_unlocked") or 1),
                }).eq("wallet", wallet).execute()
        except Exception as exc:
            log.warning(
                "gamification.quest_reward wallet=%s quest=%s reward=%s: %s",
                wallet[:18], catalog.get("quest_id"), reward_type, exc,
            )


async def _write_quest_progress(
    wallet: str,
    quest_row: dict,
    catalog: dict,
    new_progress: float,
    now_iso: str,
) -> None:
    target = float(quest_row.get("target") or catalog.get("target") or 1)
    is_done = new_progress >= target
    payload: dict[str, Any] = {"progress": round(new_progress, 2)}
    if is_done:
        payload["completed"] = True
        payload["completed_at"] = now_iso
        payload["times_completed"] = int(quest_row.get("times_completed") or 0) + 1
        payload["reward_claimed"] = True

    try:
        result = (
            db.client.table("player_quests")
            .update(payload)
            .eq("id", quest_row["id"])
            .eq("completed", False)
            .execute()
        )
        if is_done and (result.data or []):
            await _grant_quest_rewards(wallet, catalog)
    except Exception as exc:
        log.warning(
            "gamification.quest_update quest=%s wallet=%s: %s",
            catalog.get("quest_id"), wallet[:18], exc,
        )


async def _record_settlement_start(
    wallet: str,
    bet_tx_id: str,
    amount_prizm: float,
    odds: float,
    won: bool,
    won_amount: float,
    league: str,
    sport: str,
) -> bool:
    """Insert an idempotency marker for a settled bet."""
    if not db.initialized:
        return False

    bet_tx_id = str(bet_tx_id or "").strip()
    if not bet_tx_id:
        log.warning("gamification settlement skipped: empty bet_tx_id wallet=%s", wallet[:18])
        return False

    try:
        db.client.table("gamification_settlements").insert({
            "bet_tx_id": bet_tx_id,
            "wallet": wallet,
            "amount_prizm": round(float(amount_prizm or 0), 2),
            "odds": round(float(odds or 0), 4),
            "won": bool(won),
            "won_amount": round(float(won_amount or 0), 2),
            "status": "processing",
            "league": str(league or "")[:200],
            "sport": str(sport or "")[:80],
        }).execute()
        return True
    except Exception as exc:
        err = str(exc).lower()
        if "duplicate" in err or "unique" in err or "23505" in err:
            log.info(
                "gamification settlement already processed bet=%s wallet=%s",
                bet_tx_id[:18],
                wallet[:18],
            )
        else:
            log.error(
                "gamification settlement marker failed bet=%s wallet=%s: %s",
                bet_tx_id[:18],
                wallet[:18],
                exc,
            )
        return False


async def apply_settlement_bonuses(
    wallet: str,
    bet_tx_id: str,
    amount_prizm: float,
    base_payout: float,
    won: bool,
) -> dict[str, Any]:
    """
    Apply active one-bet and temporary payout bonuses to a settlement amount.

    Returns:
      {
        "payout_amount": float,
        "bonus_delta": float,
        "applied_bonuses": list[dict],
      }
    """
    result = {
        "payout_amount": round(float(base_payout or 0), 2),
        "bonus_delta": 0.0,
        "applied_bonuses": [],
    }
    if not db.initialized:
        return result

    wallet = str(wallet or "").strip().upper()
    if not wallet:
        return result

    now_iso = _now_iso()
    try:
        bonuses: list[dict] = (
            db.client.table("player_bonuses")
            .select("id,bonus_type,bonus_key,value,source,burn_on_level_up")
            .eq("wallet", wallet)
            .eq("activated", True)
            .is_("burned_at", "null")
            .gt("expires_at", now_iso)
            .order("created_at", desc=False)
            .limit(50)
            .execute()
            .data
        ) or []
    except Exception as exc:
        log.warning("gamification.apply_bonuses fetch wallet=%s bet=%s: %s", wallet[:18], bet_tx_id[:18], exc)
        return result

    burn_ids: list[int] = []
    payout = float(result["payout_amount"])

    one_bet_win_boosts = [b for b in bonuses if b.get("bonus_key") == "win_boost_50"]
    if one_bet_win_boosts:
        burn_ids.extend(int(b["id"]) for b in one_bet_win_boosts if b.get("id") is not None)

    if won and payout > 0:
        pct_bonuses = [b for b in bonuses if b.get("bonus_type") == "pct_win"]
        pct_total = sum(float(b.get("value") or 0) for b in pct_bonuses)
        if pct_total > 0:
            delta = round(payout * pct_total, 2)
            payout = round(payout + delta, 2)
            result["bonus_delta"] = round(float(result["bonus_delta"]) + delta, 2)
            result["applied_bonuses"].append({
                "type": "pct_win",
                "value": round(pct_total, 4),
                "delta": delta,
                "bonus_keys": [str(b.get("bonus_key") or "") for b in pct_bonuses],
            })

    cashback = next((b for b in bonuses if b.get("bonus_type") == "cashback"), None)
    if won and cashback and cashback.get("id") is not None:
        burn_ids.append(int(cashback["id"]))

    if not won:
        if cashback:
            value = float(cashback.get("value") or 0)
            delta = round(float(amount_prizm or 0) * value, 2)
            if delta > 0:
                payout = round(delta, 2)
                result["bonus_delta"] = round(float(result["bonus_delta"]) + delta, 2)
                result["applied_bonuses"].append({
                    "type": "cashback",
                    "value": round(value, 4),
                    "delta": delta,
                    "bonus_key": str(cashback.get("bonus_key") or ""),
                })
            if cashback.get("id") is not None:
                burn_ids.append(int(cashback["id"]))

    if burn_ids:
        try:
            db.client.table("player_bonuses").update({
                "burned_at": now_iso,
            }).in_("id", sorted(set(burn_ids))).execute()
        except Exception as exc:
            log.warning("gamification.apply_bonuses burn wallet=%s bet=%s: %s", wallet[:18], bet_tx_id[:18], exc)

    result["payout_amount"] = round(payout, 2)
    return result


def _week_dates(week_start: str | None = None) -> tuple[str, str]:
    if week_start:
        start_date = datetime.fromisoformat(str(week_start)).date()
    else:
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=now.weekday())).date()
    end_date = start_date + timedelta(days=6)
    return start_date.isoformat(), end_date.isoformat()


async def finalize_weekly_leaderboard(week_start: str | None = None) -> dict[str, Any]:
    """Persist weekly top-10 by won PRIZM and distribute rank 1-3 prizes once."""
    if not db.initialized:
        return {"ok": False, "error": "Database not configured"}

    week_start_date, week_end_date = _week_dates(week_start)
    week_start_iso = f"{week_start_date}T00:00:00+00:00"
    week_end_iso = f"{week_end_date}T23:59:59+00:00"

    try:
        settlements = (
            db.client.table("gamification_settlements")
            .select("wallet,won_amount")
            .eq("won", True)
            .eq("status", "completed")
            .gte("created_at", week_start_iso)
            .lte("created_at", week_end_iso)
            .limit(10000)
            .execute()
            .data
        ) or []
    except Exception as exc:
        log.error("gamification.finalize_weekly fetch week=%s: %s", week_start_date, exc)
        return {"ok": False, "error": str(exc)}

    totals: dict[str, float] = {}
    for row in settlements:
        wallet = str(row.get("wallet") or "").strip().upper()
        if not wallet:
            continue
        totals[wallet] = round(totals.get(wallet, 0.0) + float(row.get("won_amount") or 0), 2)

    leaderboard = [
        {"wallet": wallet, "rank": idx + 1, "won_prizm": won_prizm}
        for idx, (wallet, won_prizm) in enumerate(
            sorted(totals.items(), key=lambda item: item[1], reverse=True)[:10]
        )
    ]

    try:
        existing = (
            db.client.table("weekly_leaderboard")
            .select("wallet,prize_distributed")
            .eq("week_start", week_start_date)
            .execute()
            .data
        ) or []
        distributed = {
            str(row.get("wallet") or "").strip().upper()
            for row in existing
            if row.get("prize_distributed")
        }

        for row in leaderboard:
            wallet = row["wallet"]
            prize_distributed = wallet in distributed
            db.client.table("weekly_leaderboard").upsert(
                {
                    "week_start": week_start_date,
                    "week_end": week_end_date,
                    "wallet": wallet,
                    "rank": row["rank"],
                    "won_prizm": row["won_prizm"],
                    "prize_distributed": prize_distributed,
                },
                on_conflict="week_start,wallet",
            ).execute()

            if row["rank"] <= 3 and not prize_distributed:
                await _grant_weekly_rank_prize(wallet, row["rank"], week_start_date)
                await increment_quest_progress(wallet, "top3", delta=1.0)
                db.client.table("weekly_leaderboard").update({
                    "prize_distributed": True,
                }).eq("week_start", week_start_date).eq("wallet", wallet).execute()
                row["prize_distributed"] = True
            else:
                row["prize_distributed"] = prize_distributed

    except Exception as exc:
        log.error("gamification.finalize_weekly persist week=%s: %s", week_start_date, exc)
        return {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "week_start": week_start_date,
        "week_end": week_end_date,
        "leaderboard": leaderboard,
    }


async def _grant_weekly_rank_prize(wallet: str, rank: int, week_start: str) -> None:
    source = f"weekly_top{rank}:{week_start}"
    if rank == 1:
        await _upsert_bonus(wallet, {
            "bonus_type": "pct_win",
            "bonus_key": f"weekly_top1_temp_millionaire_{week_start}",
            "value": 0.005,
            "expires_at": _expires_iso(7),
            "burn_on_level_up": True,
            "source": source,
        })
    elif rank == 2:
        await _grant_raffle_tokens_reward(wallet, 1, source)
    elif rank == 3:
        await _grant_roulette_spins_reward(wallet, 15, source)


async def _mark_settlement_status(
    bet_tx_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update settlement marker lifecycle state."""
    if not db.initialized:
        return
    payload: dict[str, Any] = {"status": status}
    if status == "completed":
        payload["completed_at"] = _now_iso()
        payload["error_message"] = None
    elif error_message:
        payload["error_message"] = str(error_message)[:1000]
    try:
        db.client.table("gamification_settlements").update(payload).eq("bet_tx_id", bet_tx_id).execute()
    except Exception as exc:
        log.warning(
            "gamification settlement status update failed bet=%s status=%s: %s",
            str(bet_tx_id or "")[:18],
            status,
            exc,
        )


async def on_bet_settled(
    wallet: str,
    bet_tx_id: str,
    amount_prizm: float,
    odds: float,
    won: bool,
    league: str = "",
    sport: str = "",
) -> None:
    """
    Call this from v3_settler.py right after update_bet_settlement().

    Effects (in order):
      1. Upsert player_profiles (create if new)
      2. Increment total_won_prizm (won only) and total_bet_turnover (always)
      3. Award roulette_spins = floor(amount_prizm / 1500)
      4. Update quest progress
      5. Check level-up
    """
    if not db.initialized:
        return

    wallet = str(wallet or "").strip().upper()
    if not wallet:
        return

    amount = round(float(amount_prizm or 0), 2)
    odds_val = round(float(odds or 0), 4)
    won_amount = round(amount * odds_val, 2) if won else 0.0

    try:
        profile = await _get_or_create_profile(wallet)
        if not profile:
            return

        if not await _record_settlement_start(
            wallet=wallet,
            bet_tx_id=bet_tx_id,
            amount_prizm=amount,
            odds=odds_val,
            won=won,
            won_amount=won_amount,
            league=league,
            sport=sport,
        ):
            return

        # ── 1. Update counters ──────────────────────────────────────────────
        updates: dict[str, Any] = {
            "total_bet_turnover": round(
                float(profile.get("total_bet_turnover") or 0) + amount, 2
            ),
        }
        if won:
            updates["total_won_prizm"] = round(
                float(profile.get("total_won_prizm") or 0) + won_amount, 2
            )

        # ── 2. Roulette spins: 1 per 1 500 PRIZM bet ───────────────────────
        spins_earned = math.floor(amount / 1_500)
        if spins_earned > 0:
            updates["roulette_spins"] = (
                int(profile.get("roulette_spins") or 0) + spins_earned
            )

        db.client.table("player_profiles").update(updates).eq("wallet", wallet).execute()

        if spins_earned > 0:
            try:
                db.client.table("roulette_log").insert({
                    "wallet": wallet,
                    "event_type": "earned",
                    "spins_delta": spins_earned,
                    "source": f"bet:{bet_tx_id}",
                    "bet_tx_id": bet_tx_id,
                }).execute()
            except Exception as exc:
                log.warning("gamification.roulette_log bet=%s: %s", bet_tx_id[:18], exc)

        # Merge updates into local profile snapshot for quest logic
        profile.update(updates)

        # ── 3. Quest progress ───────────────────────────────────────────────
        await _update_quest_progress(
            wallet=wallet,
            profile=profile,
            amount=amount,
            odds=odds_val,
            won=won,
            won_amount=won_amount,
            single_win=won_amount if won else 0.0,
            league=league,
            sport=sport,
        )

        # ── 4. Level-up check ───────────────────────────────────────────────
        await check_level_up(wallet)
        await _mark_settlement_status(bet_tx_id, "completed")

    except Exception as exc:
        await _mark_settlement_status(bet_tx_id, "failed", error_message=str(exc))
        log.error(
            "gamification.on_bet_settled wallet=%s bet=%s: %s",
            wallet[:18], bet_tx_id[:18], exc,
        )


# ── Quest progress ─────────────────────────────────────────────────────────────

async def _update_quest_progress(
    wallet: str,
    profile: dict,
    amount: float,
    odds: float,
    won: bool,
    won_amount: float,
    single_win: float,
    league: str,
    sport: str,
) -> None:
    """
    Update progress on all non-completed quests for the player's
    current level and next level (visibility rule).
    """
    if not db.initialized:
        return

    current_level = int(profile.get("level") or 1)
    visible_levels = [current_level, current_level + 1]

    try:
        rows: list[dict] = (
            db.client.table("player_quests")
            .select("*")
            .eq("wallet", wallet)
            .eq("completed", False)
            .in_("level_unlocked", visible_levels)
            .execute()
            .data
        ) or []
    except Exception as exc:
        log.warning("gamification._update_quest_progress fetch wallet=%s: %s", wallet[:18], exc)
        return

    now_iso = _now_iso()

    for quest_row in rows:
        quest_id = quest_row.get("quest_id", "")
        catalog = QUEST_BY_ID.get(quest_id)
        if not catalog:
            continue

        old_progress = float(quest_row.get("progress") or 0)
        delta = _quest_progress_delta(
            catalog,
            amount=amount,
            odds=odds,
            won=won,
            won_amount=won_amount,
            single_win=single_win,
            league=league,
            sport=sport,
        )
        if delta is None:
            continue

        if catalog.get("quest_type") == "single_win":
            new_progress = max(old_progress, delta)
        else:
            new_progress = old_progress + delta

        await _write_quest_progress(wallet, quest_row, catalog, new_progress, now_iso)


async def increment_quest_progress(
    wallet: str,
    quest_type: str,
    delta: float = 1.0,
) -> None:
    """
    Generic helper to increment non-bet quest types:
    roulette, raffle, top3, bonus_used, prizmaster.

    Call from the relevant API handler after the action is recorded.
    """
    if not db.initialized:
        return

    wallet = str(wallet or "").strip().upper()
    target_quest_ids = _QUESTS_BY_TYPE.get(quest_type, set())
    if not target_quest_ids:
        return

    try:
        profile_rows = (
            db.client.table("player_profiles")
            .select("level")
            .eq("wallet", wallet)
            .limit(1)
            .execute()
            .data
        )
        if not profile_rows:
            return
        current_level = int(profile_rows[0].get("level") or 1)
        visible_levels = [current_level, current_level + 1]

        rows: list[dict] = (
            db.client.table("player_quests")
            .select("*")
            .eq("wallet", wallet)
            .eq("completed", False)
            .in_("level_unlocked", visible_levels)
            .execute()
            .data
        ) or []

        now_iso = _now_iso()
        for quest_row in rows:
            quest_id = quest_row.get("quest_id")
            if quest_id not in target_quest_ids:
                continue
            catalog = QUEST_BY_ID.get(quest_id)
            if not catalog:
                continue
            old_progress = float(quest_row.get("progress") or 0)
            new_progress = old_progress + delta
            await _write_quest_progress(wallet, quest_row, catalog, new_progress, now_iso)
    except Exception as exc:
        log.error("gamification.increment_quest_progress wallet=%s type=%s: %s", wallet[:18], quest_type, exc)


# ── Level-up ───────────────────────────────────────────────────────────────────

async def check_level_up(wallet: str) -> bool:
    """
    Check if the player qualifies for a level-up.

    Conditions to advance from level N to N+1:
      - total_won_prizm >= LEVELS[N+1].turnover
      - completed quest count at level N >= LEVELS[N].quests_required

    On promotion:
      - Updates level / level_name in player_profiles
      - Burns all burn_on_level_up bonuses  (Rule 3)
      - Clears prizmaster_badge             (Rule 6)
      - Initialises quests for new level and preview of next

    Returns True if the player was promoted (may promote multiple levels in
    one call if they skipped thresholds, e.g. after a big win).
    """
    if not db.initialized:
        return False

    wallet = str(wallet or "").strip().upper()
    promoted = False

    try:
        # Loop to handle multi-level jumps
        for _ in range(MAX_LEVEL):
            rows = (
                db.client.table("player_profiles")
                .select("level,total_won_prizm,prizmaster_badge,prizmaster_level")
                .eq("wallet", wallet)
                .limit(1)
                .execute()
                .data
            )
            if not rows:
                break

            profile = rows[0]
            current_level = int(profile.get("level") or 1)
            if current_level >= MAX_LEVEL:
                break

            current_info = _level_info(current_level)
            next_info    = _level_info(current_level + 1)
            won_prizm    = float(profile.get("total_won_prizm") or 0)

            # Turnover gate
            if won_prizm < next_info["turnover"]:
                break

            # Quest gate
            quests_required = current_info["quests_required"]
            if quests_required > 0:
                completed_count = (
                    db.client.table("player_quests")
                    .select("id", count="exact")
                    .eq("wallet", wallet)
                    .eq("level_unlocked", current_level)
                    .eq("completed", True)
                    .execute()
                    .count or 0
                )
                if completed_count < quests_required:
                    break

            # ── Promote ─────────────────────────────────────────────────────
            new_level = current_level + 1
            await _burn_level_up_bonuses(wallet)

            db.client.table("player_profiles").update({
                "level": new_level,
                "level_name": next_info["name"],
                "prizmaster_badge": False,   # Rule 6
                "prizmaster_level": None,
            }).eq("wallet", wallet).execute()

            # Init quests for new level + preview of level after
            await _init_quests_for_level(wallet, new_level)
            if new_level + 1 <= MAX_LEVEL:
                await _init_quests_for_level(wallet, new_level + 1)

            log.info(
                "[GAMIFICATION] Level-up wallet=%s %d→%d (%s)",
                wallet[:18], current_level, new_level, next_info["name"],
            )
            promoted = True

    except Exception as exc:
        log.error("gamification.check_level_up wallet=%s: %s", wallet[:18], exc)

    return promoted


async def _burn_level_up_bonuses(wallet: str) -> None:
    """Mark all active burn_on_level_up bonuses as burned (Rule 3)."""
    if not db.initialized:
        return
    try:
        db.client.table("player_bonuses").update({
            "burned_at": _now_iso(),
        }).eq("wallet", wallet).eq("burn_on_level_up", True).is_("burned_at", "null").execute()
    except Exception as exc:
        log.warning("gamification._burn_level_up_bonuses wallet=%s: %s", wallet[:18], exc)


# ── Roulette ───────────────────────────────────────────────────────────────────

async def spin_roulette(wallet: str, spins: int) -> list[dict]:
    """
    Spend *spins* roulette spins and return a list of prize result dicts.
    Each dict: {"prize_type": str, "prize_value": str | None}

    Prize effects are applied immediately (bonuses inserted, tokens credited).
    Returns [] on error or if the player doesn't have enough spins.
    """
    if not db.initialized:
        return []

    wallet = str(wallet or "").strip().upper()
    spins = max(1, int(spins or 1))

    try:
        # Spend through a DB-side conditional update. This prevents two
        # concurrent requests from spending the same roulette balance.
        remaining_spins = await _spend_roulette_spins(wallet, spins)
        if remaining_spins is None:
            log.warning(
                "gamification.spin_roulette: not enough spins or profile missing wallet=%s want=%d",
                wallet[:18], spins,
            )
            return []

        db.client.table("roulette_log").insert({
            "wallet": wallet,
            "event_type": "spent",
            "spins_delta": -spins,
            "source": "player",
        }).execute()

        # ── Roll prizes ─────────────────────────────────────────────────────
        prize_types = [_roll_roulette_prize() for _ in range(spins)]
        results: list[dict] = []

        for prize_type in prize_types:
            prize = _PRIZE_MAP[prize_type]
            prize_value = prize["prize_value"]

            await _apply_roulette_prize(wallet, prize_type, prize_value)

            try:
                db.client.table("roulette_log").insert({
                    "wallet": wallet,
                    "event_type": "prize",
                    "spins_delta": 0,
                    "source": "spin",
                    "prize_type": prize_type,
                    "prize_value": str(prize_value) if prize_value is not None else None,
                }).execute()
            except Exception as exc:
                log.warning("gamification.roulette_log prize=%s: %s", prize_type, exc)

            results.append({"prize_type": prize_type, "prize_value": prize_value})

        # Update roulette quests
        await increment_quest_progress(wallet, "roulette", delta=float(spins))

        return results

    except Exception as exc:
        log.error("gamification.spin_roulette wallet=%s spins=%d: %s", wallet[:18], spins, exc)
        return []


async def _apply_roulette_prize(wallet: str, prize_type: str, prize_value: str | None) -> None:
    """Materialise the effect of a single roulette prize."""
    try:
        if prize_type == "nothing":
            return

        elif prize_type == "spins_15":
            count = int(prize_value or 15)
            remaining = await _add_roulette_spins(wallet, count)
            if remaining is None:
                log.error("gamification spins prize failed wallet=%s count=%d", wallet[:18], count)
                return
            db.client.table("roulette_log").insert({
                "wallet": wallet,
                "event_type": "earned",
                "spins_delta": count,
                "source": "prize:spins_15",
                "prize_type": "spins_15",
                "prize_value": str(count),
            }).execute()

        elif prize_type == "cashback_20":
            await _upsert_bonus(wallet, {
                "bonus_type": "cashback",
                "bonus_key": "cashback_20",
                "value": float(prize_value or 0.20),
                "expires_at": _expires_iso(30),
                "burn_on_level_up": False,
                "source": "roulette",
            })

        elif prize_type == "win_boost_50":
            await _upsert_bonus(wallet, {
                "bonus_type": "pct_win",
                "bonus_key": "win_boost_50",
                "value": float(prize_value or 0.50),
                "expires_at": _expires_iso(7),
                "burn_on_level_up": True,
                "source": "roulette",
            })

        elif prize_type == "temp_millionaire":
            await _upsert_bonus(wallet, {
                "bonus_type": "pct_win",
                "bonus_key": "temp_millionaire",
                "value": float(prize_value or 0.005),
                "expires_at": _expires_iso(7),
                "burn_on_level_up": True,
                "source": "roulette",
            })

        elif prize_type == "raffle_token":
            count = int(prize_value or 1)
            remaining = await _add_raffle_tokens(wallet, count)
            if remaining is None:
                log.error("gamification raffle token prize failed wallet=%s count=%d", wallet[:18], count)
                return
            db.client.table("raffle_tokens_log").insert({
                "wallet": wallet,
                "delta": count,
                "source": "roulette",
            }).execute()

    except Exception as exc:
        log.error(
            "gamification._apply_roulette_prize wallet=%s prize=%s: %s",
            wallet[:18], prize_type, exc,
        )


async def _upsert_bonus(wallet: str, bonus: dict) -> None:
    """
    Insert a bonus respecting Rule 2 (identical bonuses don't stack).
    If an active, non-expired, non-burned bonus with the same bonus_key
    already exists, the new one is inserted as inactive (queued).
    """
    if not db.initialized:
        return
    try:
        existing = (
            db.client.table("player_bonuses")
            .select("id")
            .eq("wallet", wallet)
            .eq("bonus_key", bonus["bonus_key"])
            .is_("burned_at", "null")
            .gt("expires_at", _now_iso())
            .limit(1)
            .execute()
            .data
        )
        is_first = len(existing) == 0
        payload: dict[str, Any] = {
            "wallet": wallet,
            "activated": is_first,
            "activated_at": _now_iso() if is_first else None,
            **bonus,
        }
        db.client.table("player_bonuses").insert(payload).execute()
    except Exception as exc:
        log.warning(
            "gamification._upsert_bonus wallet=%s key=%s: %s",
            wallet[:18], bonus.get("bonus_key"), exc,
        )
