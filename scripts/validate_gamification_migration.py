#!/usr/bin/env python3
"""Validate the gamification Supabase migration before applying it remotely.

This intentionally performs static checks only. Applying DDL to Supabase must
use the project ref from .env, not a stale local Supabase CLI link.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260428000100_gamification_tables.sql"
ENV_FILE = ROOT / ".env"
TEMP_PROJECT_REF = ROOT / "supabase" / ".temp" / "project-ref"
EXPECTED_PROJECT_REF = "gvyhjqqhzyhgbbrfrbat"


REQUIRED_TABLES = (
    "player_profiles",
    "player_quests",
    "player_bonuses",
    "roulette_log",
    "raffle_tokens_log",
    "gamification_settlements",
    "raffles",
    "raffle_entries",
    "weekly_leaderboard",
)


def _env_project_ref() -> str | None:
    if not ENV_FILE.exists():
        return None
    for raw in ENV_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("SUPABASE_URL="):
            continue
        value = line.partition("=")[2].strip().strip('"').strip("'")
        match = re.search(r"https://([^.]+)\.supabase\.co", value)
        return match.group(1) if match else None
    return None


def _temp_project_ref() -> str | None:
    if not TEMP_PROJECT_REF.exists():
        return None
    return TEMP_PROJECT_REF.read_text(encoding="utf-8", errors="replace").strip()


def _require(sql: str, needle: str, failures: list[str]) -> None:
    if needle not in sql:
        failures.append(f"missing: {needle}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-link",
        action="store_true",
        help="Fail when local Supabase CLI link does not match .env project ref.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []
    if not MIGRATION.exists():
        print(f"missing migration: {MIGRATION}")
        return 1

    sql = MIGRATION.read_text(encoding="utf-8")

    env_ref = _env_project_ref()
    temp_ref = _temp_project_ref()
    if env_ref != EXPECTED_PROJECT_REF:
        failures.append(f".env SUPABASE_URL ref is {env_ref!r}, expected {EXPECTED_PROJECT_REF!r}")
    if temp_ref and temp_ref != env_ref:
        message = f"stale Supabase CLI link: .temp/project-ref={temp_ref!r}, .env ref={env_ref!r}"
        if args.strict_link:
            failures.append(message)
        else:
            warnings.append(message)

    for table in REQUIRED_TABLES:
        _require(sql, f"CREATE TABLE IF NOT EXISTS {table}", failures)
        _require(sql, f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY", failures)
        _require(sql, f"{table}_no_public_access", failures)

    _require(sql, "idx_player_quests_unique", failures)
    _require(sql, "REFERENCES player_profiles(wallet)", failures)
    _require(sql, "roulette_log_no_update", failures)
    _require(sql, "roulette_log_no_delete", failures)
    _require(sql, "raffle_tokens_log_no_update", failures)
    _require(sql, "raffle_tokens_log_no_delete", failures)
    _require(sql, "set_gamification_updated_at", failures)
    _require(sql, "НАБЛЮДАТЕЛЬ", failures)
    for function_name in (
        "spend_player_roulette_spins",
        "add_player_roulette_spins",
        "add_player_raffle_tokens",
        "enter_raffle_with_token",
    ):
        _require(sql, f"CREATE OR REPLACE FUNCTION {function_name}", failures)
        _require(sql, f"REVOKE EXECUTE ON FUNCTION {function_name}", failures)
        _require(sql, f"GRANT EXECUTE ON FUNCTION {function_name}", failures)

    if failures:
        print("gamification migration validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("gamification migration validation passed")
    for warning in warnings:
        print(f"warning: {warning}")
    print(f"project_ref={env_ref}")
    print(f"migration={MIGRATION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
