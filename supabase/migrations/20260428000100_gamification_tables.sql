-- Gamification data layer for player levels, quests, bonuses, roulette and raffles.
-- Public access is denied through RLS; backend writes with the Supabase service role.

CREATE OR REPLACE FUNCTION set_gamification_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION prevent_gamification_log_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'gamification logs are append-only';
END;
$$;

CREATE TABLE IF NOT EXISTS player_profiles (
    wallet              TEXT PRIMARY KEY,
    level               INT NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 11),
    level_name          TEXT NOT NULL DEFAULT 'НАБЛЮДАТЕЛЬ',
    total_won_prizm     NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (total_won_prizm >= 0),
    total_bet_turnover  NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (total_bet_turnover >= 0),
    roulette_spins      INT NOT NULL DEFAULT 0 CHECK (roulette_spins >= 0),
    raffle_tokens       INT NOT NULL DEFAULT 0 CHECK (raffle_tokens >= 0),
    prizmaster_badge    BOOLEAN NOT NULL DEFAULT false,
    prizmaster_level    INT CHECK (prizmaster_level BETWEEN 1 AND 11),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_player_profiles_level
    ON player_profiles (level, total_won_prizm DESC);

CREATE TABLE IF NOT EXISTS player_quests (
    id               BIGSERIAL PRIMARY KEY,
    wallet           TEXT NOT NULL REFERENCES player_profiles(wallet) ON DELETE RESTRICT,
    quest_id         TEXT NOT NULL,
    level_unlocked   INT NOT NULL DEFAULT 1 CHECK (level_unlocked BETWEEN 1 AND 11),
    progress         NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (progress >= 0),
    target           NUMERIC(20, 2) NOT NULL CHECK (target > 0),
    times_required   INT NOT NULL DEFAULT 1 CHECK (times_required > 0),
    times_completed  INT NOT NULL DEFAULT 0 CHECK (times_completed >= 0),
    completed        BOOLEAN NOT NULL DEFAULT false,
    completed_at     TIMESTAMPTZ,
    reward_claimed   BOOLEAN NOT NULL DEFAULT false,
    expires_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT player_quests_completion_time_check
        CHECK ((completed = false AND completed_at IS NULL) OR (completed = true))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_quests_unique
    ON player_quests (wallet, quest_id, level_unlocked);

CREATE INDEX IF NOT EXISTS idx_player_quests_wallet_visible
    ON player_quests (wallet, level_unlocked, completed);

CREATE INDEX IF NOT EXISTS idx_player_quests_wallet_created
    ON player_quests (wallet, created_at DESC);

CREATE TABLE IF NOT EXISTS player_bonuses (
    id                BIGSERIAL PRIMARY KEY,
    wallet            TEXT NOT NULL REFERENCES player_profiles(wallet) ON DELETE RESTRICT,
    bonus_type        TEXT NOT NULL
                         CHECK (bonus_type IN ('pct_win', 'cashback', 'roulette_spins', 'raffle_token', 'freespins')),
    bonus_key         TEXT NOT NULL,
    value             NUMERIC(10, 4) NOT NULL DEFAULT 0,
    expires_at        TIMESTAMPTZ,
    activated_at      TIMESTAMPTZ,
    activated         BOOLEAN NOT NULL DEFAULT false,
    burn_on_level_up  BOOLEAN NOT NULL DEFAULT false,
    burned_at         TIMESTAMPTZ,
    source            TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_player_bonuses_wallet_active
    ON player_bonuses (wallet, bonus_key, activated, expires_at DESC)
    WHERE burned_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_player_bonuses_wallet_created
    ON player_bonuses (wallet, created_at DESC);

CREATE TABLE IF NOT EXISTS roulette_log (
    id            BIGSERIAL PRIMARY KEY,
    wallet        TEXT NOT NULL REFERENCES player_profiles(wallet) ON DELETE RESTRICT,
    event_type    TEXT NOT NULL CHECK (event_type IN ('earned', 'spent', 'prize')),
    spins_delta   INT NOT NULL,
    source        TEXT,
    prize_type    TEXT,
    prize_value   TEXT,
    bet_tx_id     TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roulette_log_wallet_created
    ON roulette_log (wallet, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_roulette_log_bet_tx_id
    ON roulette_log (bet_tx_id)
    WHERE bet_tx_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS raffle_tokens_log (
    id          BIGSERIAL PRIMARY KEY,
    wallet      TEXT NOT NULL REFERENCES player_profiles(wallet) ON DELETE RESTRICT,
    delta       INT NOT NULL,
    source      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raffle_tokens_log_wallet_created
    ON raffle_tokens_log (wallet, created_at DESC);

CREATE TABLE IF NOT EXISTS gamification_settlements (
    bet_tx_id      TEXT PRIMARY KEY REFERENCES bets(tx_id) ON DELETE RESTRICT,
    wallet         TEXT NOT NULL REFERENCES player_profiles(wallet) ON DELETE RESTRICT,
    amount_prizm   NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (amount_prizm >= 0),
    odds           NUMERIC(12, 4) NOT NULL DEFAULT 0 CHECK (odds >= 0),
    won            BOOLEAN NOT NULL DEFAULT false,
    won_amount     NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (won_amount >= 0),
    status         TEXT NOT NULL DEFAULT 'processing'
                   CHECK (status IN ('processing', 'completed', 'failed')),
    league         TEXT,
    sport          TEXT,
    error_message  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gamification_settlements_wallet_created
    ON gamification_settlements (wallet, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_gamification_settlements_status
    ON gamification_settlements (status, created_at DESC);

CREATE TABLE IF NOT EXISTS raffles (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    questions   JSONB NOT NULL DEFAULT '[]'::jsonb,
    starts_at   TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'active', 'completed', 'cancelled')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT raffles_time_window_check
        CHECK (starts_at IS NULL OR ends_at IS NULL OR ends_at >= starts_at)
);

CREATE INDEX IF NOT EXISTS idx_raffles_status_window
    ON raffles (status, starts_at DESC, ends_at DESC);

CREATE TABLE IF NOT EXISTS raffle_entries (
    id          BIGSERIAL PRIMARY KEY,
    raffle_id   BIGINT NOT NULL REFERENCES raffles(id) ON DELETE CASCADE,
    wallet      TEXT NOT NULL REFERENCES player_profiles(wallet) ON DELETE RESTRICT,
    answers     JSONB NOT NULL DEFAULT '[]'::jsonb,
    score       INT CHECK (score IS NULL OR score >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (raffle_id, wallet)
);

CREATE INDEX IF NOT EXISTS idx_raffle_entries_wallet_created
    ON raffle_entries (wallet, created_at DESC);

CREATE TABLE IF NOT EXISTS weekly_leaderboard (
    id                 BIGSERIAL PRIMARY KEY,
    week_start         DATE NOT NULL,
    week_end           DATE NOT NULL,
    wallet             TEXT NOT NULL,
    rank               INT NOT NULL CHECK (rank > 0),
    won_prizm          NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (won_prizm >= 0),
    prize_distributed  BOOLEAN NOT NULL DEFAULT false,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (week_start, wallet),
    CONSTRAINT weekly_leaderboard_week_check CHECK (week_end >= week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_leaderboard_week_rank
    ON weekly_leaderboard (week_start DESC, rank ASC);

ALTER TABLE player_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_quests ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_bonuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE roulette_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE raffle_tokens_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE gamification_settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE raffles ENABLE ROW LEVEL SECURITY;
ALTER TABLE raffle_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_leaderboard ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS player_profiles_no_public_access ON player_profiles;
CREATE POLICY player_profiles_no_public_access ON player_profiles
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS player_quests_no_public_access ON player_quests;
CREATE POLICY player_quests_no_public_access ON player_quests
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS player_bonuses_no_public_access ON player_bonuses;
CREATE POLICY player_bonuses_no_public_access ON player_bonuses
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS roulette_log_no_public_access ON roulette_log;
CREATE POLICY roulette_log_no_public_access ON roulette_log
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS raffle_tokens_log_no_public_access ON raffle_tokens_log;
CREATE POLICY raffle_tokens_log_no_public_access ON raffle_tokens_log
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS gamification_settlements_no_public_access ON gamification_settlements;
CREATE POLICY gamification_settlements_no_public_access ON gamification_settlements
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS raffles_no_public_access ON raffles;
CREATE POLICY raffles_no_public_access ON raffles
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS raffle_entries_no_public_access ON raffle_entries;
CREATE POLICY raffle_entries_no_public_access ON raffle_entries
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS weekly_leaderboard_no_public_access ON weekly_leaderboard;
CREATE POLICY weekly_leaderboard_no_public_access ON weekly_leaderboard
    USING (false)
    WITH CHECK (false);

DROP TRIGGER IF EXISTS player_profiles_set_updated_at ON player_profiles;
CREATE TRIGGER player_profiles_set_updated_at
    BEFORE UPDATE ON player_profiles
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS player_quests_set_updated_at ON player_quests;
CREATE TRIGGER player_quests_set_updated_at
    BEFORE UPDATE ON player_quests
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS player_bonuses_set_updated_at ON player_bonuses;
CREATE TRIGGER player_bonuses_set_updated_at
    BEFORE UPDATE ON player_bonuses
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS gamification_settlements_set_updated_at ON gamification_settlements;
CREATE TRIGGER gamification_settlements_set_updated_at
    BEFORE UPDATE ON gamification_settlements
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS raffles_set_updated_at ON raffles;
CREATE TRIGGER raffles_set_updated_at
    BEFORE UPDATE ON raffles
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS raffle_entries_set_updated_at ON raffle_entries;
CREATE TRIGGER raffle_entries_set_updated_at
    BEFORE UPDATE ON raffle_entries
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS weekly_leaderboard_set_updated_at ON weekly_leaderboard;
CREATE TRIGGER weekly_leaderboard_set_updated_at
    BEFORE UPDATE ON weekly_leaderboard
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS roulette_log_no_update ON roulette_log;
CREATE TRIGGER roulette_log_no_update
    BEFORE UPDATE ON roulette_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_gamification_log_mutation();

DROP TRIGGER IF EXISTS roulette_log_no_delete ON roulette_log;
CREATE TRIGGER roulette_log_no_delete
    BEFORE DELETE ON roulette_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_gamification_log_mutation();

DROP TRIGGER IF EXISTS raffle_tokens_log_no_update ON raffle_tokens_log;
CREATE TRIGGER raffle_tokens_log_no_update
    BEFORE UPDATE ON raffle_tokens_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_gamification_log_mutation();

DROP TRIGGER IF EXISTS raffle_tokens_log_no_delete ON raffle_tokens_log;
CREATE TRIGGER raffle_tokens_log_no_delete
    BEFORE DELETE ON raffle_tokens_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_gamification_log_mutation();

CREATE OR REPLACE FUNCTION spend_player_roulette_spins(
    p_wallet TEXT,
    p_spins INT
)
RETURNS INT
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_wallet TEXT := UPPER(TRIM(COALESCE(p_wallet, '')));
    v_remaining INT;
BEGIN
    IF v_wallet = '' OR COALESCE(p_spins, 0) <= 0 THEN
        RETURN -1;
    END IF;

    UPDATE player_profiles
       SET roulette_spins = roulette_spins - p_spins
     WHERE wallet = v_wallet
       AND roulette_spins >= p_spins
     RETURNING roulette_spins INTO v_remaining;

    IF NOT FOUND THEN
        RETURN -1;
    END IF;

    RETURN v_remaining;
END;
$$;

CREATE OR REPLACE FUNCTION add_player_roulette_spins(
    p_wallet TEXT,
    p_delta INT
)
RETURNS INT
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_wallet TEXT := UPPER(TRIM(COALESCE(p_wallet, '')));
    v_remaining INT;
BEGIN
    IF v_wallet = '' OR COALESCE(p_delta, 0) <= 0 THEN
        RETURN -1;
    END IF;

    UPDATE player_profiles
       SET roulette_spins = roulette_spins + p_delta
     WHERE wallet = v_wallet
     RETURNING roulette_spins INTO v_remaining;

    IF NOT FOUND THEN
        RETURN -1;
    END IF;

    RETURN v_remaining;
END;
$$;

CREATE OR REPLACE FUNCTION add_player_raffle_tokens(
    p_wallet TEXT,
    p_delta INT
)
RETURNS INT
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_wallet TEXT := UPPER(TRIM(COALESCE(p_wallet, '')));
    v_remaining INT;
BEGIN
    IF v_wallet = '' OR COALESCE(p_delta, 0) = 0 THEN
        RETURN -1;
    END IF;

    UPDATE player_profiles
       SET raffle_tokens = raffle_tokens + p_delta
     WHERE wallet = v_wallet
       AND raffle_tokens + p_delta >= 0
     RETURNING raffle_tokens INTO v_remaining;

    IF NOT FOUND THEN
        RETURN -1;
    END IF;

    RETURN v_remaining;
END;
$$;

CREATE OR REPLACE FUNCTION enter_raffle_with_token(
    p_raffle_id BIGINT,
    p_wallet TEXT,
    p_answers JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
    v_wallet TEXT := UPPER(TRIM(COALESCE(p_wallet, '')));
    v_tokens_remaining INT;
    v_entry_id BIGINT;
    v_raffle raffles%ROWTYPE;
BEGIN
    IF p_raffle_id IS NULL THEN
        RETURN jsonb_build_object('ok', false, 'error', 'raffle_id must be an integer', 'status', 400);
    END IF;

    IF v_wallet = '' THEN
        RETURN jsonb_build_object('ok', false, 'error', 'wallet is required', 'status', 400);
    END IF;

    IF p_answers IS NULL OR jsonb_typeof(p_answers) <> 'array' THEN
        RETURN jsonb_build_object('ok', false, 'error', 'answers must be a list', 'status', 400);
    END IF;

    SELECT *
      INTO v_raffle
      FROM raffles
     WHERE id = p_raffle_id
       AND status = 'active'
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Raffle not found or not active', 'status', 404);
    END IF;

    IF v_raffle.starts_at IS NOT NULL AND v_raffle.starts_at > NOW() THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Raffle has not started', 'status', 400);
    END IF;

    IF v_raffle.ends_at IS NOT NULL AND v_raffle.ends_at < NOW() THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Raffle has ended', 'status', 400);
    END IF;

    IF EXISTS (
        SELECT 1
          FROM raffle_entries
         WHERE raffle_id = p_raffle_id
           AND wallet = v_wallet
    ) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Already entered this raffle', 'status', 409);
    END IF;

    UPDATE player_profiles
       SET raffle_tokens = raffle_tokens - 1
     WHERE wallet = v_wallet
       AND raffle_tokens >= 1
     RETURNING raffle_tokens INTO v_tokens_remaining;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Not enough raffle tokens', 'status', 400);
    END IF;

    INSERT INTO raffle_entries (raffle_id, wallet, answers)
    VALUES (p_raffle_id, v_wallet, p_answers)
    RETURNING id INTO v_entry_id;

    INSERT INTO raffle_tokens_log (wallet, delta, source)
    VALUES (v_wallet, -1, 'raffle:' || p_raffle_id::TEXT);

    RETURN jsonb_build_object(
        'ok', true,
        'wallet', v_wallet,
        'raffle_id', p_raffle_id,
        'entry_id', v_entry_id,
        'tokens_remaining', v_tokens_remaining
    );
EXCEPTION
    WHEN unique_violation THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Already entered this raffle', 'status', 409);
END;
$$;

REVOKE EXECUTE ON FUNCTION spend_player_roulette_spins(TEXT, INT) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION add_player_roulette_spins(TEXT, INT) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION add_player_raffle_tokens(TEXT, INT) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION enter_raffle_with_token(BIGINT, TEXT, JSONB) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION spend_player_roulette_spins(TEXT, INT) TO service_role;
GRANT EXECUTE ON FUNCTION add_player_roulette_spins(TEXT, INT) TO service_role;
GRANT EXECUTE ON FUNCTION add_player_raffle_tokens(TEXT, INT) TO service_role;
GRANT EXECUTE ON FUNCTION enter_raffle_with_token(BIGINT, TEXT, JSONB) TO service_role;
