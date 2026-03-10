-- Add external_id column to matches table for better tracking
ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);

-- Add unique constraint
ALTER TABLE matches
ADD CONSTRAINT matches_external_id_key UNIQUE (external_id);
