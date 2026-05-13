-- App configuration table for encrypted server-side settings.
-- Stores key/value pairs such as the encrypted hot-wallet passphrase.
-- Accessible only via the service-role key (backend); RLS blocks public access.

CREATE TABLE IF NOT EXISTS app_config (
    key        TEXT        PRIMARY KEY,
    value      TEXT        NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE app_config ENABLE ROW LEVEL SECURITY;

-- No public access at all — backend uses service-role key which bypasses RLS.
CREATE POLICY "no_public_access" ON app_config
    USING (false)
    WITH CHECK (false);
