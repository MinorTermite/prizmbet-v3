from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20260506000200_resolve_supabase_advisor_warnings.sql"


def test_advisor_hygiene_sets_security_invoker_on_public_views():
    sql = MIGRATION.read_text(encoding="utf-8")

    for view_name in (
        "v_active_matches",
        "v_financial_summary",
        "v_daily_pnl",
    ):
        assert f"ALTER VIEW public.{view_name} SET (security_invoker = true);" in sql


def test_advisor_hygiene_sets_fixed_search_path_for_trigger_functions():
    sql = MIGRATION.read_text(encoding="utf-8")

    for function_name in (
        "prevent_ledger_mutation",
        "_set_updated_at",
        "prevent_financial_events_mutation",
        "set_gamification_updated_at",
        "prevent_gamification_log_mutation",
        "spend_player_roulette_spins",
        "add_player_roulette_spins",
        "add_player_raffle_tokens",
        "enter_raffle_with_token",
    ):
        assert function_name in sql
    assert "SET search_path = public, pg_temp" in sql


def test_advisor_hygiene_drops_known_duplicate_prizm_ledger_indexes():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "DROP INDEX IF EXISTS public.idx_prizm_ledger_created_at;" in sql
    assert "DROP INDEX IF EXISTS public.idx_prizm_ledger_tx_type;" in sql
