-- Append-only financial events ledger for payouts, sweeps and manual finance actions.
-- The table is immutable: UPDATE/DELETE are blocked by trigger.
-- Public access is blocked via RLS; backend service-role writes directly.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS financial_events (
    id               BIGSERIAL PRIMARY KEY,
    event_group_id   UUID        NOT NULL DEFAULT gen_random_uuid(),
    event_type       TEXT        NOT NULL,
    direction        TEXT        NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
    status           TEXT        NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'cancelled', 'manual_review')),
    wallet_from      TEXT,
    wallet_to        TEXT,
    amount_prizm     NUMERIC(18, 2) NOT NULL DEFAULT 0,
    fee_prizm        NUMERIC(18, 8) NOT NULL DEFAULT 0,
    bet_tx_id        TEXT,
    prizm_tx_id      TEXT,
    reference_code   TEXT,
    balance_before   NUMERIC(18, 2),
    balance_after    NUMERIC(18, 2),
    initiated_by     TEXT        NOT NULL DEFAULT 'system',
    details          JSONB       NOT NULL DEFAULT '{}'::jsonb,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_financial_events_group_id
    ON financial_events (event_group_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_financial_events_type_status
    ON financial_events (event_type, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_financial_events_bet_tx_id
    ON financial_events (bet_tx_id)
    WHERE bet_tx_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_financial_events_prizm_tx_id
    ON financial_events (prizm_tx_id)
    WHERE prizm_tx_id IS NOT NULL;

ALTER TABLE financial_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS financial_events_no_public_access ON financial_events;
CREATE POLICY financial_events_no_public_access ON financial_events
    USING (false)
    WITH CHECK (false);

CREATE OR REPLACE FUNCTION prevent_financial_events_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'financial ledgers are append-only';
END;
$$;

DROP TRIGGER IF EXISTS financial_events_no_update ON financial_events;
CREATE TRIGGER financial_events_no_update
    BEFORE UPDATE ON financial_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_financial_events_mutation();

DROP TRIGGER IF EXISTS financial_events_no_delete ON financial_events;
CREATE TRIGGER financial_events_no_delete
    BEFORE DELETE ON financial_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_financial_events_mutation();

ALTER TABLE prizm_ledger ENABLE ROW LEVEL SECURITY;

ALTER TABLE prizm_ledger
    DROP CONSTRAINT IF EXISTS prizm_ledger_tx_type_check;

ALTER TABLE prizm_ledger
    ADD CONSTRAINT prizm_ledger_tx_type_check
    CHECK (tx_type IN ('deposit', 'payout', 'refund', 'fee', 'manual_adjustment', 'sweep'));

DROP POLICY IF EXISTS prizm_ledger_no_public_access ON prizm_ledger;
CREATE POLICY prizm_ledger_no_public_access ON prizm_ledger
    USING (false)
    WITH CHECK (false);

DROP TRIGGER IF EXISTS prizm_ledger_no_update ON prizm_ledger;
CREATE TRIGGER prizm_ledger_no_update
    BEFORE UPDATE ON prizm_ledger
    FOR EACH ROW
    EXECUTE FUNCTION prevent_financial_events_mutation();

DROP TRIGGER IF EXISTS prizm_ledger_no_delete ON prizm_ledger;
CREATE TRIGGER prizm_ledger_no_delete
    BEFORE DELETE ON prizm_ledger
    FOR EACH ROW
    EXECUTE FUNCTION prevent_financial_events_mutation();
