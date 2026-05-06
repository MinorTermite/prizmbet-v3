-- Resolve Supabase Advisor security/performance warnings visible after the
-- RLS lockdown migration.

ALTER VIEW public.v_active_matches SET (security_invoker = true);
ALTER VIEW public.v_financial_summary SET (security_invoker = true);
ALTER VIEW public.v_daily_pnl SET (security_invoker = true);

DO $$
BEGIN
    IF to_regprocedure('public.prevent_ledger_mutation()') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.prevent_ledger_mutation() SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public._set_updated_at()') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public._set_updated_at() SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.prevent_financial_events_mutation()') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.prevent_financial_events_mutation() SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.set_gamification_updated_at()') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.set_gamification_updated_at() SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.prevent_gamification_log_mutation()') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.prevent_gamification_log_mutation() SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.spend_player_roulette_spins(text, integer)') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.spend_player_roulette_spins(TEXT, INT) SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.add_player_roulette_spins(text, integer)') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.add_player_roulette_spins(TEXT, INT) SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.add_player_raffle_tokens(text, integer)') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.add_player_raffle_tokens(TEXT, INT) SET search_path = public, pg_temp';
    END IF;

    IF to_regprocedure('public.enter_raffle_with_token(bigint, text, jsonb)') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.enter_raffle_with_token(BIGINT, TEXT, JSONB) SET search_path = public, pg_temp';
    END IF;
END $$;

DROP INDEX IF EXISTS public.idx_prizm_ledger_created_at;
DROP INDEX IF EXISTS public.idx_prizm_ledger_tx_type;
