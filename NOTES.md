# Заметки о проделанной работе и планах

> Последнее обновление: 2026-03-01

---

## Что было исправлено

### 1. Leonbets парсер (`backend/parsers/leonbets_parser.py`) — полная перепись
- **Проблема:** парсер читал `data["sports"]` → пустой список → 0 событий
- **Решение:** правильный ключ — `data["events"]` (3500+ событий в плоском списке)
- Спорт теперь берётся из `event["league"]["sport"]["family"]`
- Имена команд из `event["nameDefault"]` (на английском)
- Маркет распознаётся по подстроке `"1Х2"` / `"1X2"` (не точное совпадение с полным названием)
- Добавлен флаг `is_live`, `match_url`
- **Результат: ~1090 матчей**

### 2. OddsAPI.io парсер (`backend/parsers/odds_api_parser.py`) — полная перепись
- **Проблема:** неверный base URL (`odds-api.io/v4` → 404)
- **Правильный URL:** `https://api.odds-api.io/v3`
- API имеет отдельные эндпоинты:
  - `/v3/events?sport=football&status=pending&apiKey=...` — список событий
  - `/v3/odds?eventId=...&bookmakers=1xbet&apiKey=...` — коэффициенты на событие
- Структура ответа: `{bookmakers: {1xbet: [{name: "ML", odds: [{home, draw, away}]}]}}`
- Маркеты: `ML` (1X2), `Double Chance`, `Spread` (фора)
- Фильтрация по топ-лигам (premier-league, la-liga, bundesliga, serie-a и т.д.)
- **Результат: ~41 матч** (rate limit на free plan — 60 событий за раз)

### 3. ApiFootball парсер (`backend/parsers/api_football_parser.py`)
- **Проблема:** free plan не поддерживает `season=2025` и `next=N`
- **Решение:** `/fixtures?date=YYYY-MM-DD` (работает без сезона, фильтрация по league_id на клиенте)
- Добавлен `/fixtures?live=all` для текущих матчей
- **Результат: ~30 матчей** (ЛЧ, АПЛ, Ла Лига, Бундеслига, Серия А, Лига 1 и др.)

### 4. Другие исправления
- `generate_json.py` — исправлена `UnicodeEncodeError` (`→` → `->`)
- `generate_json.py` — добавлен источник `oddsio_` в `_bookmaker_from_id`
- `frontend/index.html` — объединён дизайн v1 + данные v2 (тоталы, форы, LIVE-бейдж)
- `.github/workflows/update-matches.yml` — добавлено копирование медиафайлов в `frontend/`

---

## Текущий статус парсеров

| Парсер | Статус | Матчей | Причина |
|--------|--------|--------|---------|
| Leonbets | ✅ | ~1090 | Работает |
| OddsAPI.io | ✅ | ~41 | Работает (rate limit) |
| ApiFootball | ✅ | ~30 | Работает (free plan) |
| 1xBet | ❌ | 0 | Гео-блок вне РФ, нужен прокси |
| Pinnacle | ❌ | 0 | Эндпоинт 410, нужен аккаунт ps3838 |
| the-odds-api.com | ❌ | 0 | `ODDS_API_KEY` не задан в `.env`/Secrets |

---

## Что нужно сделать

### Приоритет 1 — GitHub Secrets (обязательно для workflow)
Добавить в **Settings → Secrets and variables → Actions**:
```
ODDS_API_KEY        # с the-odds-api.com → ещё ~200 матчей из топ-лиг
SUPABASE_URL        # для хранения истории (опционально)
SUPABASE_KEY
UPSTASH_REDIS_URL   # кэш и дедупликация (опционально)
UPSTASH_REDIS_TOKEN
TELEGRAM_BOT_TOKEN  # уведомления (опционально)
TELEGRAM_CHAT_ID
```

### Приоритет 2 — 1xBet (геоблок)
- Нужен прокси с российским IP
- Задать `PROXY_ENABLED=true` и `PROXY_URL=socks5://user:pass@ip:port` в Secrets
- После этого 1xBet даст 5000+ матчей со всех видов спорта

### Приоритет 3 — Leonbets: полные коэффициенты
- Сейчас `/events/all` возвращает только 1 маркет (1X2)
- Для Тотал и Фора нужен per-event запрос (пока эндпоинт не найден)
- Исследовать: `https://leon.ru/api-2/betline/event?id=...`

### Приоритет 4 — Хоккей и Баскетбол
- OddsAPI.io поддерживает `sport=basketball` и `sport=ice-hockey`
- Нужно добавить в `IO_SPORTS` и расширить `IO_TOP_SLUGS`

### Приоритет 5 — ApiFootball (платный план)
- Free plan даёт 100 запросов в день
- При 9 лигах × 4 дня = 36 запросов только на fixtures + ещё на odds
- Платный план снимает ограничение сезона и даёт `next` параметр

---

## Технические детали API

### Leonbets API
```
GET https://leon.ru/api-2/betline/events/all?ctag=ru-RU&flags=all
Response: {events: [{id, nameDefault, league: {sport: {family}}, kickoff, markets, betline, liveStatus, url}]}
Market name: "Исход 1Х2 (основное время)"
Runners: [{name: "1"|"X"|"2", price: float}]
```

### odds-api.io v3
```
GET https://api.odds-api.io/v3/events?sport=football&status=pending&apiKey=KEY
GET https://api.odds-api.io/v3/odds?eventId=ID&bookmakers=1xbet&apiKey=KEY
Bookmaker names: 1xbet, Bet365, WilliamHill, Bwin ES, Unibet (case-sensitive!)
```

### ApiFootball v3
```
GET https://v3.football.api-sports.io/fixtures?date=2026-03-01
Header: x-apisports-key: KEY
Free plan: season param не поддерживается для текущего сезона
Рабочие params: date=, live=all, id=
```
