# -*- coding: utf-8 -*-
"""
Score Enricher – обогащает frontend/matches.json реальными финальными счетами.

Источник: API-Football (v3.football.api-sports.io).
Использует существующий API_FOOTBALL_KEY из .env.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

try:
    import aiohttp
except ImportError:
    print("[score_enricher] Установите aiohttp: pip install aiohttp")
    sys.exit(1)

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_repo_root, ".env"))
except ImportError:
    pass

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
MATCHES_JSON = os.path.join(_repo_root, "frontend", "matches.json")

HEADERS = {
    "x-apisports-key": API_KEY,
}


def _normalize(name: str) -> str:
    """Убирает лишние символы для сравнения."""
    if not name: return ""
    s = name.lower()
    words = s.split()
    # Убираем типичные приставки/суффиксы, но оставляем важные маркеры (например, u20)
    words = [w for w in words if w not in ("fc", "fk", "jk", "sc", "cs", "club", "team", "the", "al", "afc", "cfc", "cd", "ac", "rc", "ud")]
    return " ".join(words).replace("-", " ").strip()


def _teams_match(our_t1: str, our_t2: str, api_t1: str, api_t2: str) -> bool:
    """Проверяет совпадение пары команд (строгий и нечёткий поиск)."""
    import difflib
    a1 = _normalize(our_t1)
    a2 = _normalize(our_t2)
    b1 = _normalize(api_t1)
    b2 = _normalize(api_t2)
    
    def core_match(name1, name2):
        if not name1 or not name2: return False
        
        # Строгая проверка возрастных групп (U20, U21 и т.д.)
        def get_age_group(n):
            for w in n.split():
                if w.startswith("u") and w[1:].isdigit():
                    return w
            return None
            
        age1 = get_age_group(name1)
        age2 = get_age_group(name2)
        if age1 and age2 and age1 != age2: return False
        if bool(age1) != bool(age2): return False # Основной состав против молодежного
            
        # Проверка пола
        def has_women(n):
            return "women" in n.split() or " (w) " in f" {n} " or "(w)" in n.replace(" ", "") or " w " in f" {n} "
        if has_women(name1) != has_women(name2): return False
            
        ratio = difflib.SequenceMatcher(None, name1, name2).ratio()
        if ratio > 0.88: return True
            
        set1 = set(name1.split())
        set2 = set(name2.split())
        if not set1 or not set2: return False
        
        intersect = set1 & set2
        meaningful_intersect = {w for w in intersect if len(w) > 2 and not (w.startswith("u") and w[1:].isdigit()) and w not in {"united", "city", "real", "athletic", "sporting", "dynamo", "boys", "girls", "women", "men"}}
        
        if meaningful_intersect:
            # Предотвращение ложных совпадений
            if ("united" in set1 ^ set2) and ("city" in set1 ^ set2): return False
            if ("real" in set1 ^ set2) and ("atletico" in set1 ^ set2): return False
            if ("inter" in set1 ^ set2) and ("ac" in set1 ^ set2): return False
            if ("aston" in set1 ^ set2) and ("west" in set1 ^ set2): return False
            return True
                
        # Если одно содержит другое целиком
        if set1.issubset(set2) or set2.issubset(set1):
            longest_word = max(set1 | set2, key=len)
            if len(longest_word) > 4:
                only_share_generic = not meaningful_intersect
                if not only_share_generic:
                    return True
            
        return False

    def pair_match(p1a, p1b, p2a, p2b):
        return core_match(p1a, p2a) and core_match(p1b, p2b)

    return pair_match(a1, a2, b1, b2) or pair_match(a1, a2, b2, b1)


def _parse_match_date(match_json_item: Dict) -> Optional[datetime]:
    """Парсит поля date и time матча из matches.json в datetime."""
    date_str = (match_json_item.get("date") or "").strip()
    time_str = (match_json_item.get("time") or "").strip()
    if not date_str: return None
    try:
        MONTHS = {
            "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
            "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
        }
        parts = date_str.split()
        day = int(parts[0])
        month = MONTHS.get(parts[1].lower(), 0)
        if not month: return None
        year = datetime.now(timezone.utc).year
        hour, minute = (int(x) for x in time_str.split(":")) if ":" in time_str else (0, 0)
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    except Exception:
        return None


async def _fetch_fixtures(session: aiohttp.ClientSession, date_str: str) -> List[Dict]:
    """Загружает ВСЕ матчи за конкретную дату из API-Football."""
    url = f"{BASE_URL}/fixtures"
    params = {"date": date_str}
    try:
        async with session.get(url, headers=HEADERS, params=params, timeout=20) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("response", [])
            print(f"[score_enricher] API-Football {r.status} for {date_str}")
    except Exception as e:
        print(f"[score_enricher] Ошибка запроса на {date_str}: {e}")
    finally:
        print(f"[score_enricher] Done fetch for {date_str}")
    return []


async def main():
    if not API_KEY:
        print("[score_enricher] API_FOOTBALL_KEY не найден — пропускаем")
        return

    if not os.path.exists(MATCHES_JSON):
        print(f"[score_enricher] {MATCHES_JSON} не найден")
        return

    with open(MATCHES_JSON, encoding="utf-8") as f:
        payload = json.load(f)

    our_matches = payload.get("matches", [])
    if not our_matches:
        return

    print(f"[score_enricher] Обогащаем {len(our_matches)} матчей...")

    # Собираем уникальные даты из нашего файла
    target_dates = set()
    for m in our_matches:
        dt = _parse_match_date(m)
        if dt:
            target_dates.add(dt.strftime("%Y-%m-%d"))
    
    # Также добавим вчерашнюю дату на случай если матч только что кончился
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    target_dates.add(yesterday)
    target_dates.add(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    all_api_fixtures = []
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_fixtures(session, ds) for ds in target_dates]
        results = await asyncio.gather(*tasks)
        for res in results:
            all_api_fixtures.extend(res)

    print(f"[score_enricher] Получено {len(all_api_fixtures)} матчей из API")

    # Строим карту счетов (учитываем только завершенные матчи)
    api_map = []
    for f in all_api_fixtures:
        status = f.get("fixture", {}).get("status", {}).get("short", "")
        if status not in ("FT", "AET", "PEN"):
            continue
        
        goals = f.get("goals", {})
        h_g = goals.get("home")
        a_g = goals.get("away")
        if h_g is None or a_g is None:
            continue
        
        teams = f.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        fdate = f.get("fixture", {}).get("date", "")
        try:
            fdt = datetime.fromisoformat(fdate.replace("Z", "+00:00"))
        except:
            continue
            
        api_map.append({
            "t1": home,
            "t2": away,
            "score": f"{h_g}:{a_g}",
            "dt": fdt
        })

    updated = 0
    for m in our_matches:
        if m.get("score"): continue  # Уже есть
        if (m.get("sport") or "football") != "football": continue # Только футбол пока

        t1 = m.get("team1", "")
        t2 = m.get("team2", "")
        dt = _parse_match_date(m)
        
        # OPTIMIZATION: Skip future matches — they can't have scores yet
        if dt:
            now = datetime.now(timezone.utc)
            if dt > now:
                continue  # Match is in the future, skip

        for candidate in api_map:
            # Только матчи в прошлом можно обогащать
            if dt and dt > datetime.now(timezone.utc):
                break
            # Сверяем по дате ±3 часа
            if dt:
                if abs((candidate["dt"] - dt).total_seconds()) > 10800:
                    continue
            
            if _teams_match(t1, t2, candidate["t1"], candidate["t2"]):
                print(f"MATCH: {t1} vs {t2} == {candidate['t1']} vs {candidate['t2']}".encode('ascii', 'replace').decode('ascii'))
                m["score"] = candidate["score"]
                updated += 1
                break
        else:
            if m.get("league", "").lower() in ["primavera 1", "championship", "premier league", "serie a", "la liga", "primeira liga"]:
                # Print why top leagues failed
                print(f"NO MATCH FOR: {t1} vs {t2} | {dt}".encode('ascii', 'replace').decode('ascii'))

    print(f"[score_enricher] Успешно добавлено {updated} счётов")

    with open(MATCHES_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
