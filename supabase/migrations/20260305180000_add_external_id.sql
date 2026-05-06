-- Add external_id column to matches table for better tracking
ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);

-- Add unique constraint
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'matches_external_id_key'
      AND conrelid = 'public.matches'::regclass
  ) THEN
    ALTER TABLE matches
    ADD CONSTRAINT matches_external_id_key UNIQUE (external_id);
  END IF;
END$$;
