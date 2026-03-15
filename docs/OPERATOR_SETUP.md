# Operator Panel Setup

## Scope
This setup enables the v3 operator panel with one owner account and assigned operator roles.

## Required environment
Set these values in `.env` on the backend host:

```env
ADMIN_VIEW_KEY=replace_with_bootstrap_key
SUPER_ADMIN_EMAIL=yatsfe9@gmail.com
SUPER_ADMIN_LOGIN=owner
ADMIN_SESSION_HOURS=12
ADMIN_PASSWORD_ITERATIONS=260000
```

Optional Google Sheets mirror:

```env
GOOGLE_SHEETS_MIRROR_ENABLED=true
GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
GOOGLE_SHEETS_WEBHOOK_TOKEN=replace_with_shared_secret
```

## Required SQL migrations
Apply both migrations in Supabase SQL Editor:

- `supabase/migrations/20260314000100_operator_audit_log.sql`
- `supabase/migrations/20260315000100_admin_auth.sql`

## Backend start
Run the API locally:

```powershell
cd C:\Users\GravMix\Desktop\prizmbet-v3
python -m backend.api.bet_intents_api
```

Default local API base:

```text
http://127.0.0.1:8081
```

## First owner bootstrap
1. Open `frontend/operator.html` locally or through the deployed site with an HTTPS backend.
2. Enter the API base.
3. Press `Connect`.
4. In `Owner Bootstrap`, enter:
   - owner email: `yatsfe9@gmail.com`
   - owner login: `owner`
   - password: choose the initial owner password
   - bootstrap key: the `ADMIN_VIEW_KEY` from `.env`
5. Submit `Create owner account`.

Bootstrap is allowed only once and only for the configured owner identity.

## Login flow
After bootstrap, all access uses named sessions:

- `super_admin`
- `operator`
- `finance`
- `viewer`

Use login or email plus password. The panel stores the session token locally and refreshes feed data on that session.

## Roles
- `super_admin`: owner only; can create and disable users
- `finance`: can mark payouts as paid
- `operator`: can review feed and audit log
- `viewer`: read-only access

## Operator panel capabilities
- live feed of accepted, rejected, won, lost and paid bets
- audit log of backend and operator events
- payout marking for finance/super admin
- user management for the owner

## Security notes
- There is no hidden backdoor.
- Owner recovery should be implemented as an explicit audited break-glass flow.
- Rotate `ADMIN_VIEW_KEY`, Telegram token and Supabase secrets before production launch.
- For internet access by multiple operators, host the backend over HTTPS. GitHub Pages cannot safely call a local HTTP API.
