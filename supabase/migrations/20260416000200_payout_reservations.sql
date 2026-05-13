-- Operational reservations for pending / in-flight payouts.
-- This table is mutable by backend service-role because reservations change state.
-- Public access is blocked via RLS.

CREATE TABLE IF NOT EXISTS payout_reservations (
    id               BIGSERIAL PRIMARY KEY,
    bet_tx_id        TEXT        NOT NULL UNIQUE REFERENCES bets(tx_id) ON DELETE CASCADE,
    sender_wallet    TEXT        NOT NULL,
    amount_prizm     NUMERIC(18, 2) NOT NULL CHECK (amount_prizm > 0),
    status           TEXT        NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'released', 'consumed', 'cancelled')),
    reservation_kind TEXT        NOT NULL DEFAULT 'payout'
                              CHECK (reservation_kind IN ('payout', 'manual_hold')),
    reason           TEXT,
    created_by       TEXT        NOT NULL DEFAULT 'system',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payout_reservations_status
    ON payout_reservations (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payout_reservations_wallet
    ON payout_reservations (sender_wallet, status);

ALTER TABLE payout_reservations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS payout_reservations_no_public_access ON payout_reservations;
CREATE POLICY payout_reservations_no_public_access ON payout_reservations
    USING (false)
    WITH CHECK (false);
