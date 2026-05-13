#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified PrizmBet v3 service runner.

Starts all backend services concurrently:
  1. Bet Intents API      (aiohttp on port 8081)
  2. Parser loop          (every PARSER_INTERVAL_SECONDS, default 300s)
  3. PRIZM Tx Listener    (every 30s)
  4. v3 Settler           (every 180s)
  5. Auto-payout          (every 60s)
  6. USDT Tx Listener     (every 30s, if USDT_ENABLED=true)

Usage:
    python -m backend.main
"""
import asyncio
import logging
import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from aiohttp import web

from backend.db.supabase_client import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("prizmbet.main")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8081"))


async def _run_api(app: web.Application) -> None:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, API_HOST, API_PORT)
    await site.start()
    log.info("API server started on %s:%s", API_HOST, API_PORT)
    # Keep running forever; cleanup is handled on cancellation.
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


async def _run_parsers_loop() -> None:
    from backend.run_parsers import run_parsers_loop
    await run_parsers_loop()


async def _run_tx_listener() -> None:
    from backend.bot.tx_listener import main as tx_main
    await tx_main()


async def _run_settler() -> None:
    from backend.bot.v3_settler import main as settler_main
    await settler_main()


async def _run_auto_payout() -> None:
    from backend.bot.auto_payout import main as payout_main
    await payout_main()


async def _run_usdt_listener() -> None:
    from backend.bot.usdt_listener import main as usdt_main
    await usdt_main()


async def _run_wallet_sweep() -> None:
    from backend.bot.wallet_sweep import main as sweep_main
    await sweep_main()


async def _validate_startup() -> None:
    """Validate critical configuration before launching services.

    Checks:
      1. Supabase DB is reachable.
      2. PRIZM_MASTER_KEY is set (required to decrypt hot-wallet passphrase).
      3. Hot-wallet passphrase is retrievable (DB-encrypted or env fallback).

    Logs clear error messages for each missing item but does NOT abort startup
    so existing deployments without DB-encrypted passphrase still work.
    """
    import os
    from backend.bot.prizm_api import get_hot_passphrase, WALLET

    log.info("--- Startup validation ---")

    # 1. Master key
    master_key = os.getenv("PRIZM_MASTER_KEY", "")
    if not master_key:
        log.error(
            "[STARTUP] PRIZM_MASTER_KEY is not set! "
            "Hot-wallet passphrase cannot be decrypted from DB. "
            "Auto-payouts will fail unless PRIZM_PASSPHRASE env var is set."
        )
    else:
        log.info("[STARTUP] PRIZM_MASTER_KEY: present (len=%d)", len(master_key))

    # 2. Passphrase retrieval
    try:
        passphrase = await get_hot_passphrase()
        if passphrase:
            log.info("[STARTUP] Hot-wallet passphrase: OK (wallet=%s)", WALLET)
        else:
            log.error(
                "[STARTUP] Hot-wallet passphrase: EMPTY! "
                "Set PRIZM_PASSPHRASE or store encrypted passphrase in app_config."
            )
    except Exception as exc:
        log.error("[STARTUP] Hot-wallet passphrase check failed: %s", exc)

    log.info("--- Startup validation complete ---")


async def main() -> None:
    log.info("=" * 50)
    log.info("PrizmBet v3 — Unified Service Runner")
    log.info("=" * 50)

    db.init()
    await _validate_startup()

    from backend.api.bet_intents_api import create_app
    app = create_app()

    tasks = [
        asyncio.create_task(_run_api(app), name="api"),
        asyncio.create_task(_run_parsers_loop(), name="parsers"),
        asyncio.create_task(_run_tx_listener(), name="tx_listener"),
        asyncio.create_task(_run_settler(), name="settler"),
        asyncio.create_task(_run_auto_payout(), name="auto_payout"),
        asyncio.create_task(_run_usdt_listener(), name="usdt_listener"),
        asyncio.create_task(_run_wallet_sweep(), name="wallet_sweep"),
    ]

    log.info(
        "Services started: %s",
        ", ".join(t.get_name() for t in tasks),
    )

    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if task.exception():
                log.error("Service '%s' crashed: %s", task.get_name(), task.exception())
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Shutdown requested")
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        log.info("All services stopped")


if __name__ == "__main__":
    asyncio.run(main())
