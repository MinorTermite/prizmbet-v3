-- PrizmBet Database Schema  
-- Execute this in Supabase SQL Editor  
  
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
  
-- Add new columns for totals and handicaps
ALTER TABLE matches 
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
 
