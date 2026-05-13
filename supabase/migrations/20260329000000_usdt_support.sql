-- Add multi-currency support: USDT TRC-20
-- payment_currency tracks which crypto was used for each bet

-- 1. Add payment_currency to bets table (default PRIZM for backwards compat)
ALTER TABLE bets
  ADD COLUMN IF NOT EXISTS payment_currency TEXT NOT NULL DEFAULT 'PRIZM';

-- 2. Add payment_currency to bet_intents
ALTER TABLE bet_intents
  ADD COLUMN IF NOT EXISTS payment_currency TEXT NOT NULL DEFAULT 'PRIZM';

-- 3. USDT checkpoint in tx_listener_state
ALTER TABLE tx_listener_state
  ADD COLUMN IF NOT EXISTS usdt_last_block_ts BIGINT DEFAULT 0;

-- 4. Index for USDT-specific queries
CREATE INDEX IF NOT EXISTS idx_bets_payment_currency ON bets (payment_currency);
CREATE INDEX IF NOT EXISTS idx_bets_currency_status ON bets (payment_currency, status);
