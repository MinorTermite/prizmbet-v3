import asyncio
import time
import logging
import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.run_parsers import run_all_parsers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

async def auto_update_loop():
    log.info("Starting Auto-Updater for Matches...")
    while True:
        try:
            log.info("Running all parsers...")
            await run_all_parsers()
            log.info("Parsers finished successfully.")
        except Exception as e:
            log.error(f"Error running parsers: {e}")
        
        # Next update in 20 minutes (1200 seconds)
        log.info("Waiting 20 minutes before next update...")
        await asyncio.sleep(1200)

if __name__ == "__main__":
    try:
        asyncio.run(auto_update_loop())
    except KeyboardInterrupt:
        log.info("Auto-Updater stopped by user.")
