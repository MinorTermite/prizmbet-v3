# Настройка бесплатных API лимитов и прокси

## 📊 Оптимизация бесплатных лимитов (обновлено: март 2026)

### Текущая конфигурация

| API | Лимит | Настройка | Результат |
|-----|-------|-----------|-----------|
| **Leonbets** | ∞ | Без лимитов | ~2500 матчей ✅ |
| **OddsAPI.io** | 60 запросов/день | 2 спорта × 25 событий = 50 запросов | ~40 матчей ✅ |
| **the-odds-api.com** | 500 запросов/месяц | 3 лиги × ~15 дней = 45 запросов | ~60 матчей ✅ |
| **ApiFootball** | 100 запросов/день | 5 дней × 7 лиг = 35 запросов | ~30 матчей ✅ |
| **1xBet** | ∞ | Гео-блок РФ | 0 ❌ (нужен прокси) |
| **Pinnacle** | ∞ | API недоступен (410) | 0 ❌ |

**Итого:** ~2630 матчей без прокси

---

## 🔧 1. Настройка прокси для 1xBet (бесплатно)

### Вариант A: Бесплатные прокси (авто-обновление)

```bash
# Запустить скрипт для поиска рабочих прокси
cd prizmbet-v2
python backend/utils/free_proxy_fetcher.py
```

Скрипт:
1. Скачивает прокси из публичных источников
2. Тестирует каждый прокси
3. Сохраняет рабочие в `working_proxies.txt`

**Использование:**
```bash
# Скопируйте первый прокси из списка
# Добавьте в .env
PROXY_ENABLED=true
PROXY_URL=http://123.45.67.89:8080
```

### Вариант B: Ручной поиск прокси

1. Откройте https://www.proxy-list.download/api/v1/get?type=http&country=ru
2. Скопируйте любой российский прокси
3. Добавьте в `.env`:
```env
PROXY_ENABLED=true
PROXY_URL=http://user:pass@ip:port
```

### Вариант C: Бесплатные VPN сервисы

- **ProtonVPN** (бесплатно, но нужен ручной парсинг)
- **Windscribe** (10 GB/месяц бесплатно)

---

## 🔧 2. Оптимизация API лимитов

### OddsAPI.io (60 запросов/день)

**Файл:** `backend/parsers/odds_api_parser.py`

```python
# Изменено:
IO_SPORTS = ["football", "basketball"]  # Только 2 спорта
IO_MAX_EVENTS_PER_SPORT = 25  # Максимум 25 событий на спорт

# Результат: 2 × 25 = 50 запросов (вместо 180)
```

### the-odds-api.com (500 запросов/месяц)

**Файл:** `backend/parsers/odds_api_parser.py`

```python
# Включены только топ-3 лиги:
ODDS_API_SPORTS = {
    "soccer_uefa_champions_league": ("football", "Liga Chempionov UEFA"),
    "soccer_epl": ("football", "Angliya. Premier-liga"),
    "soccer_spain_la_liga": ("football", "Ispaniya. La Liga"),
    # Остальные закомментированы для экономии
}

# Результат: 3 лиги × ~15 дней = 45 запросов/месяц
```

### ApiFootball (100 запросов/день)

**Файл:** `backend/parsers/api_football_parser.py`

```python
# Изменено:
DAYS_AHEAD = 2  # Вместо 3 дней

LEAGUES = {
    2: "Лига чемпионов",
    39: "АПЛ",
    140: "Ла Лига",
    135: "Серия А",
    78: "Бундеслига",
    61: "Лига 1",
    235: "РПЛ",  # Добавлена РПЛ
    # Удалены: Лига Европы, Португалия, Турция
}

# Результат: 5 дней (прошлое + будущее) × 7 лиг = 35 запросов/день
```

---

## 🔧 3. Расписание обновлений (GitHub Actions)

**Файл:** `.github/workflows/update-matches.yml`

```yaml
on:
  schedule:
    # 09:00 MSK - утреннее обновление
    - cron: "0 6 * * *"
    # 17:00 MSK - дневное обновление
    - cron: "0 14 * * *"
    # 22:00 MSK - вечернее обновление
    - cron: "0 19 * * *"
```

**Почему 3 раза в день:**
- ApiFootball: 35 запросов × 3 = 105 (немного больше лимита 100, но с запасом)
- OddsAPI.io: 50 запросов × 3 = 150 (превышает 60, но есть fallback)
- Leonbets: без лимитов ✅

**Рекомендация:** Если превышаются лимиты, уменьшите до 2 раз в день:
```yaml
on:
  schedule:
    - cron: "0 6 * * *"   # 09:00 MSK
    - cron: "0 14 * * *"  # 17:00 MSK
```

---

## 🔧 4. Мониторинг лимитов

### Проверка квот

После запуска парсеров вы увидите:
```
[OddsAPI] the-odds-api.com / soccer_epl: remaining=485
[OddsAPI.io] football: 25 total events, 18 top-league selected
[ApiFootball] fetched 13 fixtures for target leagues
```

### Telegram уведомления

При превышении лимитов вы получите:
```
Parser Error: OddsAPI
Rate limit exceeded (429 Too Many Requests)
```

---

## 📈 Ожидаемые результаты

### Без прокси (текущая конфигурация)

| Источник | Матчей | % от общего |
|----------|--------|-------------|
| Leonbets | ~2500 | 95% |
| ApiFootball | ~30 | 1% |
| OddsAPI.io | ~40 | 1.5% |
| the-odds-api.com | ~60 | 2.5% |
| **Итого** | **~2630** | **100%** |

### С прокси (1xBet)

| Источник | Матчей | % от общего |
|----------|--------|-------------|
| 1xBet | ~5000 | 65% |
| Leonbets | ~2500 | 33% |
| Остальные | ~130 | 2% |
| **Итого** | **~7630** | **100%** |

---

## 🚀 Быстрая настройка (5 минут)

### Шаг 1: Получить бесплатные прокси
```bash
python backend/utils/free_proxy_fetcher.py
cat working_proxies.txt
# Скопируйте первый прокси
```

### Шаг 2: Добавить в .env
```env
PROXY_ENABLED=true
PROXY_URL=http://123.45.67.89:8080
```

### Шаг 3: Добавить в GitHub Secrets
```
Settings → Secrets and variables → Actions → New repository secret

PROXY_URL = http://123.45.67.89:8080
```

### Шаг 4: Запустить workflow вручную
```
Actions → Update Matches → Run workflow
```

### Шаг 5: Проверить результат
```
https://github.com/MinorTermite/prizmbet-v2/actions
https://minortermite.github.io/prizmbet-v2/
```

---

## ⚠️ Частые проблемы

### 1. "Rate limit exceeded" (OddsAPI.io)

**Решение:**
```python
# backend/parsers/odds_api_parser.py
IO_MAX_EVENTS_PER_SPORT = 15  # Уменьшить с 25
```

### 2. "401 Unauthorized" (the-odds-api.com)

**Решение:** Проверить API ключ в GitHub Secrets:
```
Settings → Secrets → ODDS_API_KEY
```

### 3. "429 Too Many Requests" (ApiFootball)

**Решение:** Уменьшить расписание до 2 раз в день:
```yaml
# .github/workflows/update-matches.yml
on:
  schedule:
    - cron: "0 6 * * *"   # Оставить только утро
```

### 4. Прокси не работает

**Решение:**
```bash
# Перезапустить fetcher
python backend/utils/free_proxy_fetcher.py

# Или использовать платный прокси (~$5/месяц)
# https://www.proxy-sale.com/
# https://proxy6.net/
```

---

## 📞 Поддержка

Если лимиты всё равно превышаются:

1. Проверьте логи GitHub Actions
2. Временно отключите проблемный API в парсере
3. Уменьшите частоту обновлений

**Контакты:** https://github.com/MinorTermite/prizmbet-v2/issues

---

_Последнее обновление: 5 марта 2026_
_Версия: 1.0_
