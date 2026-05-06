# PrizmBet v3 Production Security Baseline

## Non-negotiable deployment layout

1. Put Cloudflare or another L7 DDoS/WAF provider in front of the VPS.
2. Do not expose `8081` publicly. The backend must bind to `127.0.0.1`.
3. Expose only `80/tcp`, `443/tcp`, and SSH. Restrict SSH by key and IP where possible.
4. Keep all secrets in `/opt/prizmbet/.env` with `0600` permissions, owned by `prizmbet`.
5. Rotate every secret that was ever committed, pasted into chat, logged, or stored in docs.

## Required environment values

```env
API_HOST=127.0.0.1
API_PORT=8081
ADMIN_CORS_ORIGIN=https://your-domain.com
API_MAX_REQUEST_BYTES=262144
API_RATE_LIMIT_REQUESTS=120
API_RATE_LIMIT_WINDOW=60
STATUS_RATE_LIMIT_REQUESTS=60
STATUS_RATE_LIMIT_WINDOW=60
ADMIN_RATE_LIMIT_REQUESTS=60
ADMIN_RATE_LIMIT_WINDOW=60
GAMIFICATION_RATE_LIMIT_REQUESTS=20
GAMIFICATION_RATE_LIMIT_WINDOW=60
RATE_LIMIT_MAX_KEYS=20000
GAMIFICATION_PUBLIC_MUTATIONS_ENABLED=false
```

`GAMIFICATION_PUBLIC_MUTATIONS_ENABLED=false` is intentional. Roulette and raffle entry mutate wallet-linked rewards; enabling them without wallet ownership proof lets anyone spend another player's spins/tokens.

## VPS hardening checklist

1. Run `deploy/setup.sh your-domain.com` on a clean Ubuntu 22.04+ VPS.
2. Enable HTTPS at the edge. If TLS terminates on the VPS, add a `443` nginx server and HSTS only after HTTPS works.
3. Put the domain behind Cloudflare proxy mode, enable WAF managed rules, bot fight mode, browser integrity checks, and rate limiting for `/api/*`.
4. Hide origin IP. If Cloudflare is used, allow inbound `80/443` only from current Cloudflare IP ranges.
5. Disable SSH password login in `/etc/ssh/sshd_config`: `PasswordAuthentication no`.
6. Enable unattended security upgrades.
7. Monitor `journalctl -u prizmbet`, `/var/log/nginx/error.log`, and `fail2ban-client status prizmbet-nginx-limit`.

## Secret rotation order

1. Telegram bot tokens and chat IDs used by watchdog/bots.
2. Proxy credentials in test scripts/docs.
3. Supabase service-role key.
4. `ADMIN_VIEW_KEY`, admin passwords, and operator sessions.
5. `PRIZM_MASTER_KEY`, hot wallet passphrase, and USDT private key if there was any chance of exposure.

## What code now enforces

1. Admin tokens are no longer accepted from query strings.
2. Admin CORS fails closed unless `ADMIN_CORS_ORIGIN` matches the browser origin.
3. API responses include security headers and admin responses are `no-store`.
4. Request bodies are capped by `API_MAX_REQUEST_BYTES`.
5. API/status/admin/gamification endpoints have bounded per-IP rate limits.
6. New public intent codes are 12 random uppercase alphanumeric characters.
7. Public intent/status/dashboard responses avoid raw `select("*")` exposure.
8. Operator Android WebView blocks cleartext, mixed content, file access, content access, backups, and arbitrary HTTP(S) navigation.
