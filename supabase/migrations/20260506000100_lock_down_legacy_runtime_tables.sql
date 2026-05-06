-- Lock down pre-gamification runtime tables that were created before the
-- stricter RLS baseline. The backend must use the Supabase service-role key.

ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parser_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bet_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tx_listener_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.operator_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS matches_no_public_access ON public.matches;
CREATE POLICY matches_no_public_access ON public.matches
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS parser_logs_no_public_access ON public.parser_logs;
CREATE POLICY parser_logs_no_public_access ON public.parser_logs
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS settings_no_public_access ON public.settings;
CREATE POLICY settings_no_public_access ON public.settings
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS bet_intents_no_public_access ON public.bet_intents;
CREATE POLICY bet_intents_no_public_access ON public.bet_intents
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS bets_no_public_access ON public.bets;
CREATE POLICY bets_no_public_access ON public.bets
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS tx_listener_state_no_public_access ON public.tx_listener_state;
CREATE POLICY tx_listener_state_no_public_access ON public.tx_listener_state
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS operator_audit_log_no_public_access ON public.operator_audit_log;
CREATE POLICY operator_audit_log_no_public_access ON public.operator_audit_log
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS admin_users_no_public_access ON public.admin_users;
CREATE POLICY admin_users_no_public_access ON public.admin_users
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS admin_sessions_no_public_access ON public.admin_sessions;
CREATE POLICY admin_sessions_no_public_access ON public.admin_sessions
    FOR ALL TO anon, authenticated
    USING (false)
    WITH CHECK (false);

REVOKE ALL ON TABLE
    public.matches,
    public.parser_logs,
    public.settings,
    public.bet_intents,
    public.bets,
    public.tx_listener_state,
    public.operator_audit_log,
    public.admin_users,
    public.admin_sessions
FROM anon, authenticated;

REVOKE ALL ON TABLE
    public.v_active_matches,
    public.v_financial_summary,
    public.v_daily_pnl
FROM anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.matches,
    public.parser_logs,
    public.settings,
    public.bet_intents,
    public.bets,
    public.tx_listener_state,
    public.operator_audit_log,
    public.admin_users,
    public.admin_sessions
TO service_role;

GRANT SELECT ON TABLE
    public.v_active_matches,
    public.v_financial_summary,
    public.v_daily_pnl
TO service_role;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
