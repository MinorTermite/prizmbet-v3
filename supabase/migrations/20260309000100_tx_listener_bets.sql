-- Tx Listener + Bet Intent schema

ALTER TABLE matches
ADD COLUMN IF NOT EXISTS match_status VARCHAR(20) DEFAULT 'prematch',
ADD COLUMN IF NOT EXISTS home_score INT,
ADD COLUMN IF NOT EXISTS away_score INT,
ADD COLUMN IF NOT EXISTS result_updated_at TIMESTAMP WITH TIME ZONE;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bet_status') THEN
    CREATE TYPE bet_status AS ENUM (
      'pending',
      'accepted',
      'rejected',
      'won',
      'lost',
      'refund_pending',
      'refunded',
      'paid'
    );
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS bet_intents (
  intent_hash VARCHAR(12) PRIMARY KEY,
  match_id TEXT NOT NULL,
  sender_wallet TEXT NOT NULL,
  outcome TEXT NOT NULL,
  odds_fixed NUMERIC(6,2) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
  expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') + INTERVAL '15 minutes'
);

CREATE TABLE IF NOT EXISTS bets (
  tx_id TEXT PRIMARY KEY,
  intent_hash VARCHAR(12) REFERENCES bet_intents(intent_hash),
  match_id TEXT NOT NULL,
  sender_wallet TEXT NOT NULL,
  amount_prizm NUMERIC(14,2) NOT NULL,
  odds_fixed NUMERIC(6,2) NOT NULL,
  status bet_status DEFAULT 'accepted',
  reject_reason TEXT,
  payout_tx_id TEXT UNIQUE,
  payout_amount NUMERIC(14,2) DEFAULT 0,
  block_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);
CREATE INDEX IF NOT EXISTS idx_bets_match_id ON bets(match_id);

CREATE TABLE IF NOT EXISTS tx_listener_state (
  id INT PRIMARY KEY DEFAULT 1,
  last_prizm_timestamp INT NOT NULL,
  last_tx_id TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);
