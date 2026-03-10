# Deployment Guide

## 1. Prerequisites

- Python 3.10+
- Access to Supabase project
- Access to Redis (Upstash or compatible)
- Environment variables configured via `.env`

## 2. Configuration

```bash
cp .env.example .env
```

Fill required values:
- data layer: `SUPABASE_URL`, `SUPABASE_KEY`, `UPSTASH_REDIS_*`
- parser providers: API keys used by enabled parsers
- tx listener: `MIN_BET`, `PRIZM_EPOCH`

## 3. Database

Apply Supabase migrations from `supabase/migrations/`.

Critical migration for tx-listener foundation:
- `20260309000100_tx_listener_bets.sql`

## 4. Services

### Parser job
```bash
python -m backend.run_parsers
```

### Intent API service
```bash
python -m backend.api.bet_intents_api
```

### PRIZM Tx Listener
```bash
python -m backend.bot.tx_listener
```

### Frontend static hosting
Serve `frontend/` as static site.

## 5. Operations

Recommended supervision:
- systemd / Docker restart policies for API and listener
- periodic parser scheduling via CI/cron
- structured logging aggregation and alerting

## 6. Rollback Strategy

- Keep migrations additive and reversible where possible.
- Roll back service code by git revision.
- If migration introduces issues, disable affected service first, then apply DB rollback plan.
