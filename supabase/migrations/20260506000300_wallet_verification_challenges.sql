-- Wallet ownership verification for public gamification mutations.
-- A player proves wallet control by sending the exact amount with a one-time code.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS wallet_verifications (
    wallet                  TEXT PRIMARY KEY,
    verified_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verification_tx_id      TEXT NOT NULL UNIQUE,
    verification_code       TEXT NOT NULL,
    verification_method     TEXT NOT NULL DEFAULT 'prizm_transfer_code',
    metadata                JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (wallet = UPPER(wallet)),
    CHECK (char_length(wallet) BETWEEN 3 AND 96),
    CHECK (verification_code ~ '^PB-[A-Z0-9]{6,12}$')
);

CREATE TABLE IF NOT EXISTS wallet_verification_challenges (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet                      TEXT NOT NULL,
    code                        TEXT NOT NULL UNIQUE,
    amount_prizm                NUMERIC(20, 8) NOT NULL DEFAULT 1 CHECK (amount_prizm > 0),
    recipient_wallet            TEXT NOT NULL,
    status                      TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'verified', 'expired', 'replaced')),
    tx_id                       TEXT UNIQUE,
    requested_ip                TEXT,
    user_agent                  TEXT,
    verification_block_timestamp TIMESTAMPTZ,
    expires_at                  TIMESTAMPTZ NOT NULL,
    verified_at                 TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (wallet = UPPER(wallet)),
    CHECK (char_length(wallet) BETWEEN 3 AND 96),
    CHECK (code ~ '^PB-[A-Z0-9]{6,12}$'),
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_wallet_verification_challenges_wallet_pending
    ON wallet_verification_challenges (wallet, expires_at DESC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_wallet_verification_challenges_status_expires
    ON wallet_verification_challenges (status, expires_at DESC);

CREATE INDEX IF NOT EXISTS idx_wallet_verifications_last_verified
    ON wallet_verifications (last_verified_at DESC);

ALTER TABLE wallet_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_verification_challenges ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS wallet_verifications_no_public_access ON wallet_verifications;
CREATE POLICY wallet_verifications_no_public_access ON wallet_verifications
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS wallet_verification_challenges_no_public_access ON wallet_verification_challenges;
CREATE POLICY wallet_verification_challenges_no_public_access ON wallet_verification_challenges
    USING (false)
    WITH CHECK (false);

REVOKE ALL ON wallet_verifications FROM PUBLIC, anon, authenticated;
REVOKE ALL ON wallet_verification_challenges FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON wallet_verifications TO service_role;
GRANT SELECT, INSERT, UPDATE ON wallet_verification_challenges TO service_role;

DROP TRIGGER IF EXISTS wallet_verifications_set_updated_at ON wallet_verifications;
CREATE TRIGGER wallet_verifications_set_updated_at
    BEFORE UPDATE ON wallet_verifications
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

DROP TRIGGER IF EXISTS wallet_verification_challenges_set_updated_at ON wallet_verification_challenges;
CREATE TRIGGER wallet_verification_challenges_set_updated_at
    BEFORE UPDATE ON wallet_verification_challenges
    FOR EACH ROW
    EXECUTE FUNCTION set_gamification_updated_at();

CREATE OR REPLACE FUNCTION verify_wallet_challenge(
    p_wallet TEXT,
    p_code TEXT,
    p_tx_id TEXT,
    p_block_timestamp TIMESTAMPTZ
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_wallet TEXT := UPPER(TRIM(COALESCE(p_wallet, '')));
    v_code TEXT := UPPER(TRIM(COALESCE(p_code, '')));
    v_tx_id TEXT := TRIM(COALESCE(p_tx_id, ''));
    v_block_timestamp TIMESTAMPTZ := COALESCE(p_block_timestamp, NOW());
    v_challenge wallet_verification_challenges%ROWTYPE;
BEGIN
    IF v_wallet = '' OR v_code = '' OR v_tx_id = '' THEN
        RETURN jsonb_build_object('ok', false, 'status', 400, 'error', 'wallet, code and tx_id are required');
    END IF;

    SELECT *
      INTO v_challenge
      FROM wallet_verification_challenges
     WHERE tx_id = v_tx_id
       AND status = 'verified'
     LIMIT 1;

    IF FOUND THEN
        RETURN jsonb_build_object(
            'ok', true,
            'idempotent', true,
            'wallet', v_challenge.wallet,
            'code', v_challenge.code,
            'tx_id', v_tx_id,
            'verified_at', v_challenge.verified_at
        );
    END IF;

    UPDATE wallet_verification_challenges
       SET status = 'verified',
           tx_id = v_tx_id,
           verification_block_timestamp = v_block_timestamp,
           verified_at = NOW()
     WHERE id = (
        SELECT id
          FROM wallet_verification_challenges
         WHERE wallet = v_wallet
           AND code = v_code
           AND status = 'pending'
           AND tx_id IS NULL
           AND created_at <= v_block_timestamp + INTERVAL '5 minutes'
           AND expires_at >= v_block_timestamp
         ORDER BY created_at DESC
         LIMIT 1
     )
     RETURNING * INTO v_challenge;

    IF NOT FOUND THEN
        UPDATE wallet_verification_challenges
           SET status = 'expired'
         WHERE wallet = v_wallet
           AND status = 'pending'
           AND expires_at < NOW();

        RETURN jsonb_build_object('ok', false, 'status', 404, 'error', 'No active verification challenge');
    END IF;

    INSERT INTO wallet_verifications (
        wallet,
        verified_at,
        last_verified_at,
        verification_tx_id,
        verification_code,
        metadata
    )
    VALUES (
        v_challenge.wallet,
        NOW(),
        NOW(),
        v_tx_id,
        v_code,
        jsonb_build_object(
            'challenge_id', v_challenge.id,
            'amount_prizm', v_challenge.amount_prizm,
            'recipient_wallet', v_challenge.recipient_wallet,
            'block_timestamp', v_block_timestamp
        )
    )
    ON CONFLICT (wallet) DO UPDATE
       SET last_verified_at = EXCLUDED.last_verified_at,
           verification_tx_id = EXCLUDED.verification_tx_id,
           verification_code = EXCLUDED.verification_code,
           metadata = EXCLUDED.metadata,
           updated_at = NOW();

    UPDATE wallet_verification_challenges
       SET status = 'replaced'
     WHERE wallet = v_challenge.wallet
       AND status = 'pending'
       AND id <> v_challenge.id;

    RETURN jsonb_build_object(
        'ok', true,
        'wallet', v_challenge.wallet,
        'code', v_code,
        'tx_id', v_tx_id,
        'verified_at', NOW()
    );
EXCEPTION
    WHEN unique_violation THEN
        RETURN jsonb_build_object('ok', false, 'status', 409, 'error', 'verification transaction already used');
END;
$$;

REVOKE EXECUTE ON FUNCTION verify_wallet_challenge(TEXT, TEXT, TEXT, TIMESTAMPTZ) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION verify_wallet_challenge(TEXT, TEXT, TEXT, TIMESTAMPTZ) TO service_role;
