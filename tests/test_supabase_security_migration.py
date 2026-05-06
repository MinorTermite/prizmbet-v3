from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"
LOCKDOWN = MIGRATIONS / "20260506000100_lock_down_legacy_runtime_tables.sql"

SENSITIVE_RUNTIME_TABLES = (
    "matches",
    "parser_logs",
    "settings",
    "bet_intents",
    "bets",
    "tx_listener_state",
    "operator_audit_log",
    "admin_users",
    "admin_sessions",
)

SENSITIVE_VIEWS = (
    "v_active_matches",
    "v_financial_summary",
    "v_daily_pnl",
)


def _sql() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(MIGRATIONS.glob("*.sql"))
    )


def _normalized_name(raw: str) -> str:
    return raw.removeprefix("public.").lower()


def test_sensitive_runtime_tables_have_rls_and_no_public_policies():
    sql = _sql()
    rls_tables = {
        _normalized_name(match.group(1))
        for match in re.finditer(
            r"ALTER TABLE\s+([a-zA-Z0-9_.]+)\s+ENABLE ROW LEVEL SECURITY",
            sql,
            re.IGNORECASE,
        )
    }

    for table in SENSITIVE_RUNTIME_TABLES:
        assert table in rls_tables
        assert f"{table}_no_public_access" in sql
        assert "USING (false)" in sql
        assert "WITH CHECK (false)" in sql


def test_legacy_public_roles_are_revoked_from_runtime_tables_and_views():
    sql = LOCKDOWN.read_text(encoding="utf-8")

    for table in SENSITIVE_RUNTIME_TABLES:
        assert f"public.{table}" in sql
    for view in SENSITIVE_VIEWS:
        assert f"public.{view}" in sql

    assert "FROM anon, authenticated;" in sql
    assert "TO service_role;" in sql
