from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260506000300_wallet_verification_challenges.sql"


def test_wallet_verification_migration_defines_private_tables_with_rls():
    sql = MIGRATION.read_text(encoding="utf-8")

    for table in ("wallet_verifications", "wallet_verification_challenges"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"{table}_no_public_access" in sql
        assert "USING (false)" in sql
        assert "WITH CHECK (false)" in sql
        assert f"REVOKE ALL ON {table} FROM PUBLIC, anon, authenticated;" in sql


def test_wallet_verification_migration_enforces_one_time_code_and_tx_id():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "code                        TEXT NOT NULL UNIQUE" in sql
    assert "tx_id                       TEXT UNIQUE" in sql
    assert "verification_tx_id      TEXT NOT NULL UNIQUE" in sql
    assert "CHECK (code ~ '^PB-[A-Z0-9]{6,12}$')" in sql
    assert "status IN ('pending', 'verified', 'expired', 'replaced')" in sql


def test_wallet_verification_rpc_is_atomic_service_role_only():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE OR REPLACE FUNCTION verify_wallet_challenge" in sql
    assert "SECURITY INVOKER" in sql
    assert "SET search_path = public, pg_temp" in sql
    assert "UPDATE wallet_verification_challenges" in sql
    assert "INSERT INTO wallet_verifications" in sql
    assert "ON CONFLICT (wallet) DO UPDATE" in sql
    assert "created_at <= v_block_timestamp + INTERVAL '5 minutes'" in sql
    assert "expires_at >= v_block_timestamp" in sql
    assert "REVOKE EXECUTE ON FUNCTION verify_wallet_challenge" in sql
    assert "GRANT EXECUTE ON FUNCTION verify_wallet_challenge" in sql
