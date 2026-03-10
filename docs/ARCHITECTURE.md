# PrizmBet v2 — Current Architecture

This document describes the architecture that is currently implemented in the repository.
It intentionally excludes speculative/legacy designs.

## 1) System Overview

PrizmBet consists of:
- static web frontend (`frontend/`)
- Python backend jobs/services (`backend/`)
- Supabase PostgreSQL for persistent data
- Redis for cache/rate-limit support
- PRIZM chain polling utilities for payment-driven bet intake

## 2) Main Runtime Entry Points

### Frontend
- Main UI: `frontend/index.html`
- Admin UI: `frontend/admin.html`
- PWA assets: `frontend/pwa/*`, `frontend/sw.js`, manifests

### Backend
- Parser orchestrator: `python -m backend.run_parsers`
- Health check: `python -m backend.health_check`
- Intent API: `python -m backend.api.bet_intents_api`
- Tx listener: `python -m backend.bot.tx_listener`
- Telegram operations bot: `python -m backend.bot.telegram_bot`

## 3) Data Flow (Current)

### Match/line flow
1. Provider parsers pull source data.
2. Backend normalizes matches.
3. JSON snapshots are generated for frontend (`frontend/matches.json`, `matches-today.json`).
4. Frontend renders and filters client-side.

### Bet intake flow (in transition)
1. Frontend requests short-lived bet intent (`/api/intents`).
2. Tx listener polls PRIZM transactions for the platform wallet.
3. Listener applies validation and anti-fraud rules.
4. Result is persisted in Supabase (`bets` + checkpoint state).

## 4) Storage Model

### Supabase
- Existing core tables: `matches`, `parser_logs`, `settings`
- New flow tables: `bet_intents`, `bets`, `tx_listener_state`

### Redis
- Parser-side caching and throttling support.

## 5) Known Gaps

- Legacy JSON-based bet artifacts still exist in frontend/backoffice paths and should be retired in pass 2.
- Settlement/payout path is only partially migrated to DB-first processing.
- Service boundaries are script-based; no unified process manager config is committed yet.

## 6) Security and Exposure Notes

Public documentation intentionally avoids low-level operational details of resilience mechanisms.
Implementation remains in code, but operational specifics should stay in private runbooks.
