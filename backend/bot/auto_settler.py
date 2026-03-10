import os
import sys
import json
import time
import asyncio
import logging
import aiohttp
from datetime import datetime
from pathlib import Path

# Add backend to path to import config if needed
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.bot.telegram_bot import load_bets, save_bets, fmt_bet, BOT_TOKEN
from telegram.ext import Application
from telegram import Bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

async def fetch_match_result(match_id: str):
    fixture_id = match_id.replace("apifootball_", "")
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        log.warning("API_FOOTBALL_KEY not set. Cannot fetch from API-Football.")
        return None
    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    headers = {
        "x-apisports-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    resps = data.get("response", [])
                    if resps:
                        return resps[0]
    except Exception as e:
        log.error(f"Error fetching match {fixture_id}: {e}")
    return None

def determine_win(bet_type: str, home_goals: int, away_goals: int) -> bool:
    if home_goals is None or away_goals is None:
        return False
    if bet_type == "П1":
        return home_goals > away_goals
    elif bet_type == "X":
        return home_goals == away_goals
    elif bet_type == "П2":
        return home_goals < away_goals
    elif bet_type == "1X":
        return home_goals >= away_goals
    elif bet_type == "X2":
        return away_goals >= home_goals
    elif bet_type == "12":
        return home_goals != away_goals
    
    # Обработка Тоталов (ТБ / ТМ) до 2.5
    # Формат бет: "ТБ 2.5", "ТМ 1.5"
    if bet_type.startswith("ТБ") or bet_type.startswith("ТМ"):
        try:
            parts = bet_type.split()
            if len(parts) == 2:
                t_type = parts[0] # "ТБ" или "ТМ"
                t_value = float(parts[1]) # 0.5, 1.5, 2.5
                
                # Защита: только до 2.5, по бизнес-требованию
                if t_value <= 2.5:
                    total_goals = home_goals + away_goals
                    if t_type == "ТБ":
                        return total_goals > t_value
                    elif t_type == "ТМ":
                        return total_goals < t_value
        except ValueError:
            pass # Если не удалось распарсить

    return False

async def check_match_results(bot: Bot = None):
    log.info("Checking for finished matches to settle bets...")
    bets = load_bets()
    updated = False
    admin_id = os.getenv("ADMIN_ID")

    for bet in bets:
        if bet.get("status") == "pending":
            log.info(f"Checking pending bet: {bet.get('id')} for match {bet.get('match_id')}")
            
            match_data = await fetch_match_result(str(bet.get("match_id")))
            if not match_data:
                continue
                
            status_short = match_data.get("fixture", {}).get("status", {}).get("short")
            # FT = Full Time, AET = After Extra Time, PEN = Penalties
            if status_short in ["FT", "AET", "PEN"]:
                goals = match_data.get("goals", {})
                home = goals.get("home")
                away = goals.get("away")
                
                if home is not None and away is not None:
                    is_win = determine_win(bet.get("bet_type"), int(home), int(away))
                    
                    if is_win:
                        bet["status"] = "win"
                    else:
                        bet["status"] = "loss"
                    
                    updated = True
                    log.info(f"Bet {bet['id']} settled as {bet['status']}")
                    
                    # Notify the player
                    tg_id = bet.get("tg_id")
                    if tg_id and bot:
                        try:
                            msg = f"⚽ Матч *{bet['team1']} — {bet['team2']}* завершён ({home}:{away})\n\n"
                            if bet["status"] == "win":
                                msg += f"🎉 Ваша ставка *{bet['bet_type']}* сыграла!\n"
                                msg += f"💰 Выигрыш: *{bet['payout']} PZM*\n"
                                msg += f"⏳ Ожидайте перевод от администратора."
                            else:
                                msg += f"❌ Ставка *{bet['bet_type']}* не сыграла.\nСчёт: {home}:{away}."
                            await bot.send_message(chat_id=tg_id, text=msg, parse_mode='Markdown')
                        except Exception as e:
                            log.error(f"Failed to send notification to {tg_id}: {e}")
                    
                    # Notify the ADMIN about winning bets for manual payout
                    if bet["status"] == "win" and admin_id and bot:
                        try:
                            admin_msg = (
                                f"💸 *ВЫПЛАТА ТРЕБУЕТСЯ*\n\n"
                                f"Ставка: `{bet['id']}`\n"
                                f"Игрок: `{bet.get('sender', 'N/A')}`\n"
                                f"TG: `{tg_id}`\n"
                                f"Матч: {bet['team1']} — {bet['team2']} ({home}:{away})\n"
                                f"Тип: {bet['bet_type']} @ {bet['coef']}\n"
                                f"Сумма ставки: {bet['amount']} PZM\n"
                                f"*К выплате: {bet['payout']} PZM*"
                            )
                            await bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode='Markdown')
                        except Exception as e:
                            log.error(f"Failed to notify admin: {e}")

    if updated:
        save_bets(bets)
        log.info("Saved updated bet statuses.")

async def main():
    log.info("Starting Auto-Settler Service...")
    app = None
    if BOT_TOKEN:
        app = Application.builder().token(BOT_TOKEN).build()
    
    while True:
        try:
            await check_match_results(app.bot if app else None)
        except Exception as e:
            log.error(f"Error in auto settler: {e}")
        
        await asyncio.sleep(60 * 15)  # Check every 15 minutes

if __name__ == "__main__":
    asyncio.run(main())
