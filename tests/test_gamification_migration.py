from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260428000100_gamification_tables.sql"
BACKEND_FILES = [
    ROOT / "backend" / "bot" / "gamification.py",
    ROOT / "backend" / "api" / "bet_intents_api.py",
]


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


def migration_sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_gamification_migration_defines_required_tables_with_rls():
    sql = migration_sql()

    for table in REQUIRED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"{table}_no_public_access" in sql
        assert "USING (false)" in sql
        assert "WITH CHECK (false)" in sql


def test_gamification_migration_matches_backend_table_usage():
    sql = migration_sql()
    backend = "\n".join(path.read_text(encoding="utf-8") for path in BACKEND_FILES)
    used_tables = set(re.findall(r'table\("([^"]+)"\)', backend))
    gamification_tables = {
        table
        for table in used_tables
        if table.startswith(("player_", "roulette_", "raffle", "weekly_", "gamification_"))
    }

    assert gamification_tables <= set(REQUIRED_TABLES)
    assert gamification_tables == set(REQUIRED_TABLES) - {"raffle_entries"}
    for table in gamification_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "CREATE TABLE IF NOT EXISTS raffle_entries" in sql
    assert "INSERT INTO raffle_entries" in sql


def test_gamification_logs_are_append_only():
    sql = migration_sql()

    for table in ("roulette_log", "raffle_tokens_log"):
        assert f"{table}_no_update" in sql
        assert f"{table}_no_delete" in sql
        assert "prevent_gamification_log_mutation" in sql


def test_gamification_schema_has_runtime_indexes_and_utf8_default():
    sql = migration_sql()

    assert "idx_player_quests_unique" in sql
    assert "idx_player_quests_wallet_visible" in sql
    assert "idx_player_bonuses_wallet_active" in sql
    assert "idx_gamification_settlements_status" in sql
    assert "idx_raffles_status_window" in sql
    assert "idx_weekly_leaderboard_week_rank" in sql
    assert "\u041d\u0410\u0411\u041b\u042e\u0414\u0410\u0422\u0415\u041b\u042c" in sql


def test_gamification_schema_has_atomic_balance_rpcs():
    sql = migration_sql()

    for function_name in (
        "spend_player_roulette_spins",
        "add_player_roulette_spins",
        "add_player_raffle_tokens",
        "enter_raffle_with_token",
    ):
        assert f"CREATE OR REPLACE FUNCTION {function_name}" in sql
        assert f"REVOKE EXECUTE ON FUNCTION {function_name}" in sql
        assert f"GRANT EXECUTE ON FUNCTION {function_name}" in sql

    assert "AND roulette_spins >= p_spins" in sql
    assert "AND raffle_tokens + p_delta >= 0" in sql
    assert "AND raffle_tokens >= 1" in sql
    assert "INSERT INTO raffle_entries" in sql
    assert "INSERT INTO raffle_tokens_log" in sql


def test_gamification_settlement_hook_is_guarded_by_unique_marker():
    source = (ROOT / "backend" / "bot" / "gamification.py").read_text(encoding="utf-8")

    assert 'db.client.table("gamification_settlements").insert' in source
    assert '"bet_tx_id": bet_tx_id' in source
    assert 'if not await _record_settlement_start(' in source
    assert source.index("if not await _record_settlement_start(") < source.index(
        'db.client.table("player_profiles").update(updates)'
    )
