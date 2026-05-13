-- PrizmBet Database Schema  
-- Migrated via Supabase CLI

-- Matches table  
CREATE TABLE IF NOT EXISTS matches (  
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,  
    sport VARCHAR(50) DEFAULT 'football',  
    league VARCHAR(255) NOT NULL,  
    home_team VARCHAR(255) NOT NULL,  
    away_team VARCHAR(255) NOT NULL,  
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,  
    odds_home DECIMAL(10, 2),  
    odds_draw DECIMAL(10, 2),  
    odds_away DECIMAL(10, 2),  
    bookmaker VARCHAR(100),  
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()  
);  

-- Add columns
ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS score VARCHAR(50),
ADD COLUMN IF NOT EXISTS total_value DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS total_over DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS total_under DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS handicap_1_value DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS handicap_1 DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS handicap_2_value DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS handicap_2 DECIMAL(10,2);

-- Indexes  
CREATE INDEX IF NOT EXISTS idx_matches_sport ON matches(sport);  
CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league);  
CREATE INDEX IF NOT EXISTS idx_matches_match_time ON matches(match_time);  
CREATE INDEX IF NOT EXISTS idx_matches_bookmaker ON matches(bookmaker);
CREATE INDEX IF NOT EXISTS idx_matches_total ON matches(total_value);
CREATE INDEX IF NOT EXISTS idx_matches_handicap ON matches(handicap_1_value, handicap_2_value);  

-- ✅ Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_matches_composite ON matches(sport, match_time DESC);
CREATE INDEX IF NOT EXISTS idx_matches_time_desc ON matches(match_time DESC);
CREATE INDEX IF NOT EXISTS idx_matches_active ON matches(sport, match_time DESC) WHERE score IS NULL;
CREATE INDEX IF NOT EXISTS idx_matches_league_sport ON matches(league, sport) WHERE score IS NULL;

-- Unique index for deduplication
CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_unique 
ON matches(
    LOWER(TRIM(home_team)), 
    LOWER(TRIM(away_team)), 
    match_time, 
    bookmaker
);

-- Index for totals filtering
CREATE INDEX IF NOT EXISTS idx_matches_totals 
ON matches(total_value, match_time DESC) 
WHERE total_over IS NOT NULL AND score IS NULL;

-- VIEW for fast queries
CREATE OR REPLACE VIEW v_active_matches AS
SELECT id, sport, league, home_team, away_team, match_time,
       odds_home, odds_draw, odds_away, total_value, total_over, total_under
FROM matches 
WHERE score IS NULL AND match_time > NOW() - INTERVAL '48 hours'
ORDER BY match_time ASC;
  
-- Parser logs table  
CREATE TABLE IF NOT EXISTS parser_logs (  
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,  
    parser_name VARCHAR(100) NOT NULL,  
    status VARCHAR(20) NOT NULL,  
    matches_count INTEGER DEFAULT 0,  
    error_message TEXT,  
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()  
);  
  
-- Settings table  
CREATE TABLE IF NOT EXISTS settings (  
    key VARCHAR(100) PRIMARY KEY,  
    value JSONB NOT NULL,  
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()  
);
