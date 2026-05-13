# Development Guide

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Common commands

```bash
# parsers
python -m backend.run_parsers

# health
python -m backend.health_check

# tx listener
python -m backend.bot.tx_listener

# intent API
python -m backend.api.bet_intents_api

# static frontend
python3 -m http.server 8000 -d frontend
```

## Engineering conventions

- Keep root-level files minimal; put docs in `docs/`, scripts in `scripts/`.
- Prefer incremental refactors over broad rewrites.
- Keep time fields in UTC across services and DB writes.
- Preserve idempotency at DB constraint level for chain/event consumers.

## Frontend maintainability path

Current state is static HTML/CSS/JS and should remain stable for now.
Recommended path:
1. keep current structure and continue extracting utility modules;
2. isolate config constants and API adapters;
3. migrate large pages incrementally only when business logic is stable.

## Backend maintainability path

Current backend includes parsers, bot scripts, and DB adapters.
Recommended path:
1. keep parser providers in `backend/parsers`;
2. centralize service entrypoints in `backend/api` and `backend/bot`;
3. add tests around listener/intent flow before deeper settlement refactor.
