-- Financial views and ledger for PRIZM accounting
-- 2026-03-23

-- 1. Indexes for financial queries
CREATE INDEX IF NOT EXISTS idx_bets_created_at ON bets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bets_status_created ON bets(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bets_sender_wallet ON bets(sender_wallet);

-- 2. Payout timestamp column
ALTER TABLE bets ADD COLUMN IF NOT EXISTS payout_sent_at TIMESTAMPTZ;

-- 3. Aggregate financial summary (computed from bets)
CREATE OR REPLACE VIEW v_financial_summary AS
SELECT
  COUNT(*) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded'))
    AS total_bets,
  COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0)
    AS total_deposits,
  COALESCE(SUM(payout_amount) FILTER (WHERE status = 'paid'), 0)
    AS total_payouts,
  COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0)
    - COALESCE(SUM(payout_amount) FILTER (WHERE status = 'paid'), 0)
    AS gross_profit,
  CASE
    WHEN COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0) > 0
    THEN ROUND(
      (COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0)
       - COALESCE(SUM(payout_amount) FILTER (WHERE status = 'paid'), 0))
      / COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0) * 100
    , 2)
    ELSE 0
  END AS hold_pct,
  COALESCE(SUM(payout_amount) FILTER (WHERE status = 'won'), 0)
    AS pending_payouts,
  COUNT(*) FILTER (WHERE status = 'won') AS won_unpaid_count,
  COUNT(*) FILTER (WHERE status = 'paid') AS paid_count,
  COUNT(*) FILTER (WHERE status = 'refund_pending') AS refund_pending_count,
  COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('refund_pending','refunded')), 0)
    AS total_refunded
FROM bets;

-- 4. Daily P&L breakdown
CREATE OR REPLACE VIEW v_daily_pnl AS
SELECT
  DATE(created_at AT TIME ZONE 'UTC') AS day,
  COUNT(*) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded'))
    AS bet_count,
  COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0)
    AS deposits,
  COALESCE(SUM(payout_amount) FILTER (WHERE status = 'paid'), 0)
    AS payouts,
  COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0)
    - COALESCE(SUM(payout_amount) FILTER (WHERE status = 'paid'), 0)
    AS profit,
  CASE
    WHEN COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0) > 0
    THEN ROUND(
      (COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0)
       - COALESCE(SUM(payout_amount) FILTER (WHERE status = 'paid'), 0))
      / COALESCE(SUM(amount_prizm) FILTER (WHERE status IN ('accepted','won','lost','paid','refund_pending','refunded')), 0) * 100
    , 2)
    ELSE 0
  END AS hold_pct
FROM bets
GROUP BY DATE(created_at AT TIME ZONE 'UTC')
ORDER BY day DESC;

-- 5. PRIZM ledger — append-only journal of all PRIZM movements
CREATE TABLE IF NOT EXISTS prizm_ledger (
  id BIGSERIAL PRIMARY KEY,
  tx_type TEXT NOT NULL CHECK (tx_type IN ('deposit','payout','refund','fee','manual_adjustment')),
  bet_tx_id TEXT REFERENCES bets(tx_id),
  prizm_tx_id TEXT,
  wallet TEXT NOT NULL,
  amount_prizm NUMERIC(14,2) NOT NULL,
  fee_prizm NUMERIC(14,2) DEFAULT 0,
  balance_after NUMERIC(14,2),
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prizm_ledger_created ON prizm_ledger(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prizm_ledger_type ON prizm_ledger(tx_type);
CREATE INDEX IF NOT EXISTS idx_prizm_ledger_wallet ON prizm_ledger(wallet);
