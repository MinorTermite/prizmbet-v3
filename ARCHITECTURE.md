# PrizmBet v3 — Full Architecture & Documentation

## What is PrizmBet

PrizmBet is a crypto-powered sports betting platform built on PRIZM blockchain (with USDT TRC-20 support in progress). Users select a match, create a coupon (intent), send crypto to a wallet, and the system automatically accepts the bet, settles the result, and pays out winnings.

---

## Architecture Overview

```
+---------------+     +--------------+     +------------------+
|  Android App  |---->|   nginx      |---->|  aiohttp :8081   |
|  (WebView)    |     |  (reverse    |     |  (Python)        |
+---------------+     |   proxy)     |     +--------+---------+
                      +--------------+              |
+---------------+                          +--------v---------+
|  Browser      |------------------------->|  Supabase        |
|  (PWA)        |                          |  (PostgreSQL)    |
+---------------+                          +--------+---------+
                                                    |
+---------------+     +--------------+     +--------v---------+
|  PRIZM Node   |<----|  Tx Listener |<----|  Redis Cache     |
|  (blockchain) |     |  (30s poll)  |     |  (Upstash)       |
+---------------+     +--------------+     +------------------+
```

**Domain:** https://prizmbet.net
**Server:** 103.217.253.13 (QloudHost VPS, Ubuntu 22.04)
**Database:** Supabase (hosted PostgreSQL)
**Cache:** Upstash Redis

---

## Backend (Python / aiohttp)

### Entry Point: `backend/main.py`

Starts 5 concurrent async services:

| Service | Interval | Purpose |
|---------|----------|---------|
| **API Server** | port 8081 | REST API for frontend and admin panel |
| **Parser Loop** | 300s | Parses odds from OddsAPI, 1xBet, Leonbets, Pinnacle |
| **Tx Listener** | 30s | Monitors PRIZM blockchain for incoming transfers |
| **Settler** | 180s | Settles bets based on match final scores |
| **Auto-Payout** | 60s | Automatically sends winnings to user wallets |

### Directory Structure

```
backend/
├── main.py                 # Service runner (entry point)
├── config.py               # Environment variable config
├── health_check.py         # System health monitoring
├── run_parsers.py          # Parser orchestration
│
├── api/
│   ├── bet_intents_api.py  # Main REST API (1100+ lines, all routes)
│   └── generate_json.py    # Generates frontend/matches.json from DB
│
├── bot/
│   ├── tx_listener.py      # PRIZM blockchain monitor
│   ├── v3_settler.py       # Automatic bet settlement
│   ├── auto_payout.py      # Automatic PRIZM payouts to winners
│   ├── prizm_api.py        # PRIZM node API communication
│   ├── telegram_bot.py     # Telegram notification sender
│   └── auto_settler.py     # Legacy settler (deprecated)
│
├── parsers/
│   ├── base_parser.py      # Base class with HTTP connection pooling
│   ├── odds_api_parser.py  # the-odds-api.com parser
│   ├── xbet_parser.py      # 1xBet JSON API parser
│   ├── leonbets_parser.py  # Leonbets JSON API parser
│   ├── pinnacle_parser.py  # Pinnacle / ps3838 parser
│   └── api_football_parser.py # ApiFootball (RapidAPI) parser
│
├── db/
│   └── supabase_client.py  # Supabase/PostgreSQL client wrapper
│
└── utils/
    ├── admin_auth.py       # PBKDF2-SHA256 password hashing, session tokens
    ├── bet_views.py        # Bet serialization helpers
    ├── operator_audit.py   # Audit logging for admin actions
    ├── operator_alerts.py  # Operator notification system
    ├── telegram_v3.py      # V3-specific Telegram helpers
    ├── wallet_crypto.py    # AES-256-GCM encryption for wallet passphrase
    ├── proxy_manager.py    # Free proxy rotation for parsers
    ├── rate_limiter.py     # API rate limiting
    ├── redis_client.py     # Upstash Redis client
    └── team_mapping.py     # Team name normalization across sources
```

### API Endpoints

#### Public Endpoints (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/public/create-intent` | Create a bet coupon. Body: `{match_id, sender_wallet, outcome, amount_prizm, payment_currency}`. Returns `intent_hash` |
| GET | `/api/public/intent-status/{hash}` | Poll coupon/bet status. Returns current status, payout info |
| GET | `/api/public/wallet-pending` | Get pending intent for a given wallet address |
| GET | `/api/public/matches` | Fetch all active matches with odds from Redis/DB cache |
| GET | `/api/health` | Health check. Returns `{"ok": true}` |

#### Admin Endpoints (require `X-Admin-Session` header)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/bootstrap-admin` | (bootstrap) | Create first super_admin user. Requires `X-Admin-Key` = ADMIN_VIEW_KEY |
| GET | `/api/bootstrap-state` | public | Check if bootstrap is available |
| POST | `/api/admin/login` | public | Login with login+password, returns session token |
| POST | `/api/admin/logout` | any | Invalidate session |
| GET | `/api/admin/bets` | operator+ | List bets with filters (status, date, wallet) |
| GET | `/api/admin/bets/{tx_id}` | operator+ | Get detailed bet info |
| POST | `/api/admin/bets/{tx_id}/mark-paid` | operator+ | Mark bet as paid (requires payout_tx_id) |
| POST | `/api/admin/bets/{tx_id}/refund` | operator+ | Refund a bet |
| GET | `/api/admin/export/csv` | finance+ | Export bets to CSV |
| GET | `/api/admin/audit-log` | operator+ | Fetch operator audit log |
| GET | `/api/admin/financial/summary` | finance+ | PnL summary (total bets, wins, losses, edge) |
| GET | `/api/admin/financial/daily-pnl` | finance+ | Daily PnL for last N days |
| GET | `/api/admin/users` | super_admin | List all admin users |
| POST | `/api/admin/users/create` | super_admin | Create new admin user |
| POST | `/api/admin/users/{id}/edit` | super_admin | Edit admin user |
| POST | `/api/admin/users/{id}/toggle` | super_admin | Enable/disable user |

#### CORS Headers (all responses)

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, X-Admin-Key, X-Admin-Session, Authorization
```

---

## Database (Supabase / PostgreSQL)

### Migrations: `supabase/migrations/`

### Core Tables

#### `matches` — Sports events with odds

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Match ID |
| sport | VARCHAR | 'football', 'esports', 'basketball', etc. |
| league | TEXT | League name |
| home_team | TEXT | Home team name |
| away_team | TEXT | Away team name |
| match_time | TIMESTAMP | Scheduled kick-off time |
| score | TEXT | Final score (null until finished) |
| is_live | BOOLEAN | Currently playing |
| odds_home | NUMERIC | Odds for home win (P1) |
| odds_draw | NUMERIC | Odds for draw (X) |
| odds_away | NUMERIC | Odds for away win (P2) |
| total_value | NUMERIC | Total line value |
| total_over | NUMERIC | Over odds |
| total_under | NUMERIC | Under odds |

#### `bet_intents` — Created coupons (pre-payment)

| Column | Type | Description |
|--------|------|-------------|
| intent_hash | VARCHAR(12) (PK) | Unique coupon code (shown to user) |
| match_id | UUID (FK) | Reference to match |
| sender_wallet | TEXT | User's PRIZM wallet address |
| outcome | TEXT | 'p1', 'x', 'p2', 'p1x', 'px2', 'p12' |
| odds_fixed | NUMERIC | Odds locked at intent creation |
| payment_currency | TEXT | 'PRIZM' or 'USDT' |
| created_at | TIMESTAMP | When coupon was created |
| expires_at | TIMESTAMP | +15 minutes from creation |

#### `bets` — Confirmed bets (after blockchain payment detected)

| Column | Type | Description |
|--------|------|-------------|
| tx_id | TEXT (PK) | PRIZM transaction ID |
| intent_hash | TEXT (FK) | Reference to bet_intent |
| match_id | UUID (FK) | Reference to match |
| sender_wallet | TEXT | User's wallet |
| amount_prizm | NUMERIC | Bet amount |
| odds_fixed | NUMERIC | Locked odds |
| status | ENUM | pending/accepted/rejected/won/lost/refunded/paid |
| reject_reason | TEXT | Why rejected (if applicable) |
| payout_amount | NUMERIC | Calculated winnings (amount * odds) |
| payout_tx_id | TEXT | Blockchain TX ID of payout |
| block_timestamp | TIMESTAMP | When TX was detected on chain |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

#### `admin_users` — Operator accounts

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT (PK) | Auto-increment |
| login | TEXT (UNIQUE) | Login name |
| email | TEXT | Email address |
| password_hash | TEXT | PBKDF2-SHA256 (260k iterations) |
| role | ENUM | super_admin / operator / finance / viewer |
| is_active | BOOLEAN | Account enabled |
| last_login_at | TIMESTAMP | Last login time |

#### `admin_sessions` — Active sessions

| Column | Type | Description |
|--------|------|-------------|
| token_hash | TEXT (PK) | SHA256 of session token |
| admin_user_id | BIGINT (FK) | Reference to admin_users |
| expires_at | TIMESTAMP | +12 hours from login |
| last_seen_at | TIMESTAMP | Updated on each API call |

#### `operator_audit_log` — Action journal

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT (PK) | Auto-increment |
| event_type | TEXT | Action type (login, mark_paid, refund, etc.) |
| tx_id | TEXT | Related bet TX ID |
| payload | JSONB | Full action details |
| created_at | TIMESTAMP | When action occurred |

#### `tx_listener_state` — Blockchain sync checkpoint

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK, always 1) | Single row |
| last_prizm_timestamp | BIGINT | Last processed block timestamp |
| last_tx_id | TEXT | Last processed transaction ID |

#### `app_config` — Key-value settings

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT (PK) | Setting name |
| value | TEXT | Setting value |
| updated_at | TIMESTAMP | Last update |

Key: `hot_wallet_passphrase_enc` — AES-256-GCM encrypted PRIZM passphrase

### Views

- `v_active_matches` — Matches in next 48h without final score
- `v_financial_summary` — Aggregate PnL (total bets, wins, losses, house edge %)
- `v_daily_pnl` — Day-by-day profit/loss breakdown

### Bet Status Lifecycle

```
         create-intent
              |
              v
          bet_intents (expires in 15 min)
              |
         [PRIZM transfer detected]
              |
              v
           pending --> accepted --> won  --> paid (auto-payout)
                          |          |
                          |        lost (no payout)
                          |
                       rejected (with reject_reason)
                          |
                       refunded (manual by operator)
```

---

## Frontend (HTML / CSS / JavaScript)

### Structure

```
frontend/
├── index.html              # Main page (PWA-enabled)
├── admin.html              # Admin login page
├── operator.html           # Operator panel
├── intent-lab.html         # Bet intent debug tool
├── live_index.html         # Live events view
├── matches.json            # Auto-generated by parsers
├── matches-today.json      # Today's matches subset
├── app-version.json        # Android app version info
├── manifest.json           # PWA manifest
├── sw.js                   # Service Worker for offline
│
├── css/
│   ├── base.css            # Core layout styles
│   ├── styles.css          # Main theme styles
│   ├── smart-flow.css      # Bet flow UI styles
│   └── operator.css        # Operator panel styles
│
├── js/
│   ├── app.js              # Main entry point
│   ├── api.js              # Supabase/REST API client
│   ├── operator.js         # Operator console logic
│   ├── operator-shell.js   # Operator UI shell
│   ├── operator-i18n.js    # Operator translations
│   ├── intent-lab.js       # Intent debug interface
│   └── modules/
│       ├── app.js          # Match data filtering and rendering
│       ├── bet_slip.js     # Smart coupon flow (900+ lines)
│       ├── payment_rails.js# PRIZM/USDT wallet config
│       ├── filters.js      # Sport/league/time filters
│       ├── history_ui.js   # Bet history display
│       ├── i18n.js         # RU/EN internationalization
│       ├── notifications.js# Toast notification system
│       ├── storage.js      # LocalStorage helpers
│       ├── ui.js           # Match card rendering
│       └── utils.js        # Date/time utilities
│
└── apk/
    └── prizmbet.apk        # Android APK for download
```

### Betting Flow (Frontend)

1. User browses matches on `index.html`
2. Selects outcome (P1 / X / P2) on a match card
3. Enters bet amount in the smart coupon panel
4. Clicks "Create Coupon" -> POST `/api/public/create-intent`
5. Receives `intent_hash` (6-12 char code) + QR code with wallet address
6. User opens PRIZM wallet app, sends amount with message = `intent_hash`
7. Frontend polls `/api/public/intent-status/{hash}` every 15 seconds
8. Status transitions: `waiting` -> `accepted` -> `won`/`lost` -> `paid`

### Payment Rails (`payment_rails.js`)

```javascript
[
  { key: 'prizm',      code: 'PRIZM', chain: 'PRIZM',    mode: 'auto',    wallet: 'PRIZM-4N7T-...' },
  { key: 'usdt-trc20', code: 'USDT',  chain: 'TRON',     mode: 'manual',  wallet: '' },
  { key: 'usdt-erc20', code: 'USDT',  chain: 'Ethereum', mode: 'pending', wallet: '' },
  { key: 'btc',        code: 'BTC',   chain: 'Bitcoin',   mode: 'pending', wallet: '' },
]
```

- `auto` — fully automated (blockchain listener + auto-payout)
- `manual` — operator confirms payment receipt
- `pending` — not yet implemented

### Bet Limits

| Currency | Min | Max |
|----------|-----|-----|
| PRIZM | 1500 | 30000 |
| USDT | 5 | 500 |

---

## Android App

### Structure

```
prizmbet_android/
├── app/src/main/
│   ├── java/com/prizmbet/app/
│   │   ├── SplashActivity.java       # Animated splash screen launcher
│   │   ├── PremiumSplashView.java    # Custom Canvas-based cyber animation
│   │   └── MainActivity.java         # WebView loading https://prizmbet.net
│   ├── assets/prizmbet-v3/           # Local static files (CSS, JS, images)
│   └── res/layout/
│       ├── activity_splash.xml       # Splash layout
│       └── activity_main.xml         # WebView + SwipeRefreshLayout
├── app/build.gradle                  # Build config, signing, versioning
└── gradle/
```

### How It Works

1. **SplashActivity** launches with `PremiumSplashView` (animated cyber splash, ~3.8s)
2. After animation completes, auto-launches **MainActivity**
3. **MainActivity** loads `https://prizmbet.net/` in WebView
4. Static assets (CSS, JS, fonts) are served from local `assets/` for speed
5. `matches.json` and `matches-today.json` always fetched from network (live data)
6. Pull-to-refresh triggers `refreshData()` JavaScript function
7. App checks `app-version.json` for available updates

### Key Constants (MainActivity.java)

```java
SITE_URL     = "https://prizmbet.net/"
VERSION_URL  = "https://prizmbet.net/app-version.json"
ALLOWED_HOSTS = {"prizmbet.net", "www.prizmbet.net", "minortermite.github.io",
                 "fonts.googleapis.com", "fonts.gstatic.com"}
```

### Build

```bash
cd prizmbet_android
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/Prizmbet_1.2.apk
```

---

## Payment System

### PRIZM (Fully Automatic)

```
User -> PRIZM transfer -> Blockchain -> Tx Listener -> Supabase -> Settler -> Auto-Payout -> User
```

**How Tx Listener works (`tx_listener.py`):**
1. Every 30s, calls PRIZM node `getBlockchainTransactions` API
2. Filters for transfers TO the hot wallet
3. Reads `message` field from each transaction
4. Matches message to `intent_hash` in `bet_intents` table
5. Validates: amount in range, intent not expired, sender matches, match not started
6. If valid: creates `bets` record with status='accepted'
7. If invalid: creates `bets` record with status='rejected' + `reject_reason`

**Rejection Reasons:**
- `INVALID_INTENT` — Intent not found or expired
- `DUST_DONATION` — Amount below minimum bet
- `LATE_BET` — Transfer arrived after safe window (120s grace)
- `MATCH_ALREADY_STARTED` — Match already in progress
- `SENDER_MISMATCH` — Wallet doesn't match intent
- `AMBIGUOUS_WALLET_INTENT` — Multiple active intents for same wallet

**How Auto-Payout works (`auto_payout.py`):**
1. Every 60s, finds bets with status='won' and payout_amount > 0
2. Checks hot wallet balance >= payout amount
3. Sends PRIZM via `sendMoney` API (max: MAX_BET * 10 per payout)
4. Large payouts require manual operator confirmation
5. Records `payout_tx_id`, sets status='paid'
6. Alerts operator via Telegram if balance < 5000 PRIZM

**PRIZM Wallet Security:**
- Hot wallet passphrase encrypted with AES-256-GCM
- Master key from `PRIZM_MASTER_KEY` env var (32-byte base64url)
- Encrypted passphrase stored in `app_config.hot_wallet_passphrase_enc`
- Fallback: `PRIZM_PASSPHRASE` env var (plaintext, legacy, not recommended)

### USDT TRC-20 (Manual, In Progress)

- Frontend sends `payment_currency: 'USDT'` in intent creation
- Bet limits: min 5, max 500 USDT
- Operator manually confirms payment receipt via admin panel
- No auto-payout yet for USDT

---

## Bet Settlement

### How Settler works (`v3_settler.py`)

1. Every 180s, fetches all bets with status='accepted'
2. For each bet, checks if the match has a final `score`
3. Parses score (e.g. "2:1") into home_goals / away_goals
4. Determines win/loss based on outcome:

| Outcome | Win Condition |
|---------|---------------|
| p1 | home_goals > away_goals |
| x | home_goals == away_goals |
| p2 | away_goals > home_goals |
| p1x | home_goals >= away_goals |
| p12 | home_goals != away_goals |
| px2 | away_goals >= home_goals |

5. Sets status='won' + payout_amount = amount * odds_fixed, OR status='lost'
6. Sends Telegram notification with result details

---

## Admin Panel

### Access

- **URL:** `https://prizmbet.net/admin.html` (login) -> `operator.html` (dashboard)
- **First setup:** POST `/api/bootstrap-admin` with `X-Admin-Key` header

### Roles & Permissions

| Feature | super_admin | operator | finance | viewer |
|---------|:-----------:|:--------:|:-------:|:------:|
| View bets | Yes | Yes | Yes | Yes |
| Mark as paid | Yes | Yes | No | No |
| Refund bet | Yes | Yes | No | No |
| Export CSV | Yes | No | Yes | No |
| Financial summary | Yes | No | Yes | No |
| Daily PnL | Yes | No | Yes | No |
| Audit log | Yes | Yes | Yes | No |
| Manage users | Yes | No | No | No |

### Session Management

- Session token returned on login (12-hour expiry)
- Token hash stored in `admin_sessions` table
- `last_seen_at` updated on each API request
- Expired sessions auto-cleaned

---

## Telegram Bot

**Config:** `V3_TELEGRAM_BOT_TOKEN` + `V3_TELEGRAM_CHAT_ID`

### Notifications Sent

| Event | Content |
|-------|---------|
| Bet accepted | Amount, wallet, match, outcome, odds |
| Bet settled | Won/Lost, payout amount, match result |
| Payout sent | PRIZM amount, recipient wallet, TX ID |
| Parser run | Total matches parsed, errors if any |
| Low balance | Wallet balance dropped below 5000 PRIZM |
| Admin action | Logins, manual payouts, refunds |

---

## Data Parsers

### Sources

| Parser | Source | Sports | Markets |
|--------|--------|--------|---------|
| OddsAPIParser | the-odds-api.com | Football, Basketball, Tennis | 1X2, Totals, Handicaps |
| XBetParser | 1xBet JSON API | Multiple | Multiple |
| LeonbetsParser | Leonbets JSON API | Football, Esports | 1X2, Totals |
| PinnacleParser | Pinnacle (ps3838) | Multiple | Multiple |
| ApiFootballParser | RapidAPI | Football only | 1X2, Live scores |

### Pipeline

1. Fetch from external API
2. Parse JSON -> extract teams, odds, match time
3. Normalize team names (via `team_mapping.py`)
4. Check Redis for deduplication (1-hour TTL)
5. Upsert into Supabase `matches` table
6. Generate `frontend/matches.json` and `matches-today.json`
7. Send Telegram summary

### Connection Pooling (BaseParser)

- TCP pool limit: 50 global, 10 per host
- DNS caching: 5-minute TTL
- SOCKS proxy support via `aiohttp-socks`
- User-Agent rotation via `fake-useragent`

---

## Deployment

### Server Setup (`deploy/setup.sh`)

1. Install: Python3, pip, git, nginx, certbot, ufw
2. Firewall: allow 22, 80, 443
3. Clone repo to `/root/prizmbet-v3`
4. Python venv + install requirements
5. Copy `.env` with credentials
6. Create systemd service
7. Configure nginx reverse proxy
8. SSL with certbot (Let's Encrypt)

### Service Management

```bash
systemctl start prizmbet      # Start
systemctl stop prizmbet       # Stop
systemctl restart prizmbet    # Restart
systemctl status prizmbet     # Check status
journalctl -u prizmbet -f     # Live logs
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name prizmbet.net www.prizmbet.net;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name prizmbet.net www.prizmbet.net;
    ssl_certificate /etc/letsencrypt/live/prizmbet.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prizmbet.net/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Quick Deploy (from local machine)

```bash
# SSH to server
ssh root@103.217.253.13

# Pull latest code
cd /root/prizmbet-v3 && git pull origin main

# Restart service
systemctl restart prizmbet

# Check health
curl -s https://prizmbet.net/health
# {"ok": true}
```

---

## Environment Variables (.env)

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Service role JWT token |
| `PRIZM_HOT_WALLET` | PRIZM wallet address for receiving bets |
| `PRIZM_MASTER_KEY` | AES-256-GCM encryption key (base64url) |
| `ADMIN_VIEW_KEY` | Bootstrap key for first admin creation |
| `SUPER_ADMIN_EMAIL` | Default super admin email |
| `SUPER_ADMIN_LOGIN` | Default super admin login |
| `V3_TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `V3_TELEGRAM_CHAT_ID` | Telegram chat for notifications |
| `V3_TELEGRAM_CHAT_IDS` | Comma-separated chat IDs for broadcast |
| `ODDS_API_KEY` | the-odds-api.com API key |
| `UPSTASH_REDIS_REST_URL` | Redis cache URL |
| `UPSTASH_REDIS_REST_TOKEN` | Redis auth token |
| `MIN_BET` | Minimum bet amount (default: 10) |
| `MAX_BET` | Maximum bet amount (default: 30000) |

---

## Python Dependencies (`requirements.txt`)

```
aiohttp>=3.9.0
redis>=4.6.0
supabase>=2.0.0
python-dotenv>=1.0.0
fake-useragent>=1.4.0
pytest>=7.4.3
pytest-asyncio>=0.21.1
Brotli>=1.1.0
aiohttp-socks>=0.8.0
upstash-redis>=1.6.0
```

---

## Security Notes

- **Passwords:** PBKDF2-SHA256 with 260,000 iterations
- **Sessions:** Token hash stored in DB, IP tracking, 12h expiry
- **Wallet passphrase:** Encrypted AES-256-GCM in app_config table
- **CORS:** Open for public endpoints, header-restricted for admin
- **Bootstrap key:** Prevents unauthorized first-admin creation
- **Rate limiting:** Applied to public API endpoints

---

## Key File Quick Reference

| What | File |
|------|------|
| Backend entry point | `backend/main.py` |
| All API routes | `backend/api/bet_intents_api.py` |
| PRIZM blockchain monitor | `backend/bot/tx_listener.py` |
| Bet settlement logic | `backend/bot/v3_settler.py` |
| Auto-payout logic | `backend/bot/auto_payout.py` |
| Frontend main page | `frontend/index.html` |
| Bet coupon JS logic | `frontend/js/modules/bet_slip.js` |
| Payment config | `frontend/js/modules/payment_rails.js` |
| Admin panel | `frontend/operator.html` + `js/operator.js` |
| Android main activity | `prizmbet_android/.../MainActivity.java` |
| Android splash | `prizmbet_android/.../PremiumSplashView.java` |
| DB migrations | `supabase/migrations/` |
| Deploy scripts | `deploy/setup.sh`, `deploy/update.sh` |
| Systemd service | `/etc/systemd/system/prizmbet.service` |
| Nginx config | `/etc/nginx/sites-available/prizmbet` |
