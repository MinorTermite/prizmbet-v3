# PrizmBet v2 — Контекст проекта

## 📋 Обзор проекта

**PrizmBet v2** — современная платформа для криптовалютных ставок на спорт с агрегацией коэффициентов от нескольких букмекеров. Проект представляет собой full-stack веб-приложение с асинхронными парсерами букмекерских API и реактивным frontend.

**GitHub:** https://github.com/MinorTermite/prizmbet-v2  
**Версия:** 2.1 (март 2026)  
**Статус:** ✅ Рабочая версия (~1160 матчей)

### Ключевые возможности v2.1
- ✅ **Тоталы (больше/меньше)** для всех видов спорта
- ✅ **Гандикапы (форы)** для всех видов спорта
- ✅ **The Odds API v4** — официальная агрегация коэффициентов
- ✅ **1xBet JSON API** с gzip-декомпрессией
- ✅ **Leonbets JSON API** с динамическим парсингом рынков (~1090 матчей)
- ✅ **OddsAPI.io v3** — альтернативный источник
- ✅ **ApiFootball** — топ-лиги Европы
- ✅ Автоматический fallback между парсерами
- ✅ Мониторинг квот API
- ✅ Нормализация команд (устранение дубликатов)

### Технологический стек

| Компонент | Технологии |
|-----------|------------|
| **Frontend** | HTML5, CSS3, Vanilla JS, Three.js (3D-фон), PWA |
| **Backend** | Python 3.11, asyncio, aiohttp |
| **БД** | Supabase (PostgreSQL) — до 500MB бесплатно |
| **Кэш** | Upstash Redis — 10,000 команд/день |
| **Инфраструктура** | Docker, GitHub Actions, GitHub Pages |
| **Мониторинг** | Telegram Bot, health check скрипты |

---

## 🚀 Быстрый старт

### 1. Клонирование
```bash
git clone https://github.com/YOUR_USERNAME/prizmbet-v2.git
cd prizmbet-v2
```

### 2. Настройка окружения
```bash
copy .env.example .env
```

Заполните `.env`:
```env
# The Odds API
ODDS_API_KEY=your_the_odds_api_key_here

# API-Football / RapidAPI
API_FOOTBALL_KEY=your_api_football_key_here

# odds-api.io
ODDS_API_IO_KEY=your_odds_api_io_key_here

# Supabase (PostgreSQL)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Upstash Redis
UPSTASH_REDIS_URL=your_upstash_url
UPSTASH_REDIS_TOKEN=your_upstash_token

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Pinnacle / ps3838 (Basic Auth)
PINNACLE_LOGIN=your_pinnacle_login
PINNACLE_PASSWORD=your_pinnacle_password

# GitHub
GITHUB_TOKEN=your_github_token

# Parser Settings
PROXY_ENABLED=false
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Запуск
```bash
# Запуск парсеров
python -m backend.run_parsers

# Health check
python -m backend.health_check

# Генерация matches.json
python -m backend.api.generate_json
```

### Docker
```bash
docker-compose up -d
docker-compose logs -f parser
```

---

## 📁 Структура проекта

```
prizmbet-v2/
├── backend/
│   ├── parsers/
│   │   ├── base_parser.py          # Базовый класс: fetch, parse, save, run
│   │   ├── odds_api_parser.py      # OddsAPI (the-odds-api.com + odds-api.io)
│   │   ├── xbet_parser.py          # 1xBet (JSON API)
│   │   ├── leonbets_parser.py      # Leonbets (JSON API)
│   │   ├── pinnacle_parser.py      # Pinnacle / ps3838 (JSON API)
│   │   └── api_football_parser.py  # ApiFootball (RapidAPI)
│   ├── db/
│   │   └── supabase_client.py      # Клиент Supabase (PostgreSQL)
│   ├── utils/
│   │   ├── redis_client.py         # Клиент Redis (Upstash)
│   │   ├── telegram.py             # Telegram-уведомления и алерты
│   │   ├── team_mapping.py         # Нормализация названий команд
│   │   ├── rate_limiter.py         # Rate limiting и ротация User-Agent
│   │   └── proxy_manager.py        # Управление прокси
│   ├── api/
│   │   └── generate_json.py        # Генерация frontend/matches.json
│   ├── bot/                        # Telegram bot модули
│   ├── config.py                   # Конфигурация из переменных окружения
│   ├── run_parsers.py              # Оркестратор: запускает все парсеры
│   ├── health_check.py             # Проверка здоровья системы
│   ├── score_enricher.py           # Обогащение матчей финальными счетами
│   └── requirements.txt            # Python зависимости
│
├── frontend/
│   ├── index.html                  # Главная страница (PWA, 1867 строк)
│   ├── css/
│   │   └── base.min.css            # Минифицированные стили
│   ├── js/
│   │   ├── app.js                  # Main entry point
│   │   └── modules/
│   │       ├── api.js              # API logic
│   │       ├── filters.js          # Фильтрация и сортировка матчей
│   │       ├── bet_slip.js         # Купон ставок
│   │       ├── storage.js          # LocalStorage утилиты
│   │       ├── notifications.js    # Уведомления и favorites
│   │       ├── history_ui.js       # История ставок UI
│   │       ├── ui.js               # Рендеринг матчей
│   │       └── utils.js            # Общие утилиты
│   └── matches.json                # Генерируется из парсеров
│
├── config/
│   └── supabase_schema.sql         # Схема БД PostgreSQL
│
├── .github/
│   └── workflows/
│       └── update-matches.yml      # GitHub Actions (каждые 3 часа)
│
├── netlify/
│   └── functions/                  # Serverless функции для Netlify
│
├── .env.example                    # Шаблон переменных окружения
├── Dockerfile                      # Docker-образ
├── docker-compose.yml              # Docker Compose
├── netlify.toml                    # Настройки Netlify (headers, redirects)
└── package.json                    # Node.js зависимости (минимальные)
```

---

## 🏗️ Архитектура

### Поток данных
```
API букмекеров → Парсеры (asyncio) → Нормализация → Redis (дедупликация) → Supabase (PostgreSQL)
                                                                         ↓
                                                               generate_json.py → frontend/matches.json
                                                                         ↓
                                                               Telegram Bot (мониторинг)
```

### Детальная схема работы
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ИСТОЧНИКИ ДАННЫХ (API букмекеров)                   │
│  OddsAPI  │  1xBet  │  Leonbets  │  Pinnacle  │  ApiFootball               │
└──────────┬────────────┬───────────┬────────────┬────────────┬──────────────┘
           │            │           │            │            │
           ▼            ▼           ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        run_parsers.py (asyncio.gather)                      │
│  BaseParser: fetch() → parse() → normalize() → save_matches()               │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌─────────────────┐ ┌────────────┐ ┌────────────────────┐
│ Redis (Upstash) │ │  Supabase  │ │  generate_json.py  │
│ Дедупликация    │ │ PostgreSQL │ │ frontend/          │
│ TTL: 1 час      │ │ matches    │ │   matches.json     │
│ Throttling      │ │ parser_logs│ │                    │
└─────────────────┘ └────────────┘ └────────────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Telegram Bot    │
                  │  Отчёты парсеров │
                  │  Алерты (30 мин) │
                  └──────────────────┘
```

---

## 🔑 Ключевые компоненты

### BaseParser (`backend/parsers/base_parser.py`)
Базовый класс для всех парсеров:
- `fetch()` — HTTP-запрос с retry и rate limiting
- `parse()` — абстрактный метод (реализуется в подклассах)
- `save_matches()` — нормализация → дедупликация в Redis → сохранение в Supabase
- `run()` — запуск цикла с Telegram-отчётом и throttled-алертом

### Нормализация команд (`backend/utils/team_mapping.py`)
TeamNormalizer устраняет дублирование матчей от разных букмекеров:
- Словарь TEAM_ALIASES (EPL, La Liga, Serie A, Bundesliga, Ligue 1, РПЛ)
- `normalize(name)` → приводит к нижнему регистру, ищет в словаре

### Redis (Upstash) (`backend/utils/redis_client.py`)
- **Дедупликация матчей**: `match:{parser}:{YYYY-MM-DD}:{home}:{away}` TTL: 1 час
- **Throttling алертов**: `alert_throttle:{cooldown_key}` TTL: 30 минут

### Supabase (`backend/db/supabase_client.py`)
Таблицы PostgreSQL:
- `matches` — данные матчей от всех букмекеров
- `parser_logs` — история запусков парсеров
- `settings` — настройки системы

### generate_json.py (`backend/api/generate_json.py`)
Конвертирует данные парсеров в формат frontend:
- Запускает все парсеры через `asyncio.gather()`
- Фильтрует матчи старше 3 дней
- Рассчитывает double chance коэффициенты
- Сохраняет в `frontend/matches.json`

### Frontend (`frontend/js/app.js`)
Модульная архитектура:
- `filters.js` — фильтрация по видам спорта, лигам, поиск
- `bet_slip.js` — купон ставок, расчет выплат
- `storage.js` — LocalStorage для избранного и истории
- `notifications.js` — push-уведомления, favorites
- `ui.js` — рендеринг карточек матчей

---

## 📊 База данных

### Схема Supabase (`config/supabase_schema.sql`)

```sql
CREATE TABLE matches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sport VARCHAR(50) DEFAULT 'football',
    league VARCHAR(255) NOT NULL,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
    odds_home DECIMAL(10, 2),
    odds_draw DECIMAL(10, 2),
    odds_away DECIMAL(10, 2),
    total_value DECIMAL(10,2),
    total_over DECIMAL(10,2),
    total_under DECIMAL(10,2),
    handicap_1_value DECIMAL(10,2),
    handicap_1 DECIMAL(10,2),
    handicap_2_value DECIMAL(10,2),
    handicap_2 DECIMAL(10,2),
    bookmaker VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Индексы для производительности:**
- `idx_matches_composite` — (sport, match_time DESC) для быстрых фильтров
- `idx_matches_unique` — уникальность по командам + дате
- `idx_matches_totals` — для фильтрации по тоталам

---

## 🔧 Команды разработки

### Основные команды
```bash
# Запуск всех парсеров
python -m backend.run_parsers

# Генерация matches.json
python -m backend.api.generate_json

# Health check системы
python -m backend.health_check

# Обогащение счетов
python backend/score_enricher.py

# Тестирование парсеров
python backend/test_leonbets.py
python backend/test_odds.py
```

### Статус парсеров
```bash
# После запуска вы увидите:
Leonbets completed in 2.3s - 1090 matches
OddsAPI completed in 5.1s - 41 matches
ApiFootball completed in 1.8s - 30 matches
1xBet completed in 0.5s - 0 matches (geo-blocked)
Pinnacle completed in 0.3s - 0 matches (410 Gone)

Total matches parsed: 1161
[generate_json] Wrote 1161 matches -> frontend/matches.json
```

### Docker команды
```bash
# Запуск контейнеров
docker-compose up -d

# Просмотр логов
docker-compose logs -f parser

# Остановка
docker-compose down
```

### GitHub Actions
Workflow запускается:
- По расписанию: `0 6 * * *` и `0 14 * * *` (09:00 и 17:00 MSK)
- Вручную: Actions → Run workflow
- При push в main

---

## 🎨 Frontend особенности

### Формат matches.json
```json
{
  "last_update": "2026-03-05T12:00:00+03:00",
  "source": "multi-parser",
  "total": 50,
  "matches": [
    {
      "sport": "football",
      "league": "Лига чемпионов УЕФА",
      "id": "odds_12345",
      "date": "5 мар",
      "time": "20:00",
      "team1": "Реал Мадрид",
      "team2": "Барселона",
      "p1": "2.50",
      "x": "3.20",
      "p2": "2.80",
      "p1x": "1.45",
      "p12": "1.35",
      "px2": "1.50",
      "total_value": 2.5,
      "total_over": "1.90",
      "total_under": "1.90",
      "source": "OddsAPI",
      "is_live": false
    }
  ]
}
```

### UI компоненты
- **3D фон** — Three.js космическая анимация
- **PWA** — Progressive Web App с offline поддержкой
- **Тёмная тема** — deep midnight с electric violet акцентами
- **Адаптивность** — мобильные, планшеты, десктоп
- **Фильтры** — по видам спорта, лигам, поиск по командам
- **Избранное** — сохранение матчей в LocalStorage
- **Купон ставок** — расчет выплат, история ставок

---

## 🔒 Безопасность

```
✅ HTTPS (SSL от Let's Encrypt)
✅ Секреты только в переменных окружения (.env, GitHub Secrets)
✅ Rate limiting запросов к API букмекеров
✅ Ротация User-Agent
✅ Throttling алертов (защита от спама в Telegram)
✅ Graceful shutdown (соединения закрываются при любом завершении)
✅ CORS настроен правильно (netlify.toml)
✅ Content Security Policy headers
```

---

## ⚡ Производительность

### Оптимизации парсеров (v2.1)
- ✅ Все парсеры запускаются параллельно (`asyncio.gather`)
- ✅ Rate limiting и случайные задержки между запросами
- ✅ Дедупликация через Redis (не записывает повторно в БД)
- ✅ Connection pooling и DNS кэширование (TTL 300 сек)
- ✅ Gzip/deflate/brotli сжатие
- ✅ Нормализация команд (устранение дубликатов)
- ✅ Graceful shutdown (соединения закрываются в `finally`)

### Реальные показатели (март 2026)
| Метрика | Значение |
|---------|----------|
| Leonbets парсинг | ~2-3 сек (1090 матчей) |
| OddsAPI.io парсинг | ~5-6 сек (41 матч) |
| ApiFootball парсинг | ~1-2 сек (30 матчей) |
| Общее время | ~8-10 сек |
| matches.json размер | ~150-200 KB |
| GitHub Actions запуск | ~40-60 сек |

### Кэш
- TTL матча: 1 час
- TTL алерта: 30 минут
- matches.json кэш: 5 минут (CDN)

### Frontend метрики
- Размер HTML: ~50KB (минимизирован)
- Размер matches.json: ~150-200KB (1160 матчей)
- First Contentful Paint: <1s
- Time to Interactive: <2s
- CSS: base.min.css (17 KB сжатый)

---

## 📈 Масштабируемость

### Текущие лимиты
| Сервис | Лимит | Использование |
|--------|-------|---------------|
| GitHub Actions | 2000 мин/месяц | ~40 мин/месяц |
| GitHub Pages | 100GB bandwidth/месяц | — |
| GitHub Pages | 125K serverless запросов/месяц | — |
| Supabase | 500MB БД | — |
| Upstash Redis | 10,000 команд/день | — |
| Google Sheets | 10M ячеек | — |

---

## 🐛 Отладка

### Логи парсеров
```bash
# Docker логи
docker-compose logs -f parser

# Health check
python -m backend.health_check

# Проверка подключения
# Redis: через Upstash Dashboard или CLI
# Supabase: SQL Editor → SELECT * FROM matches LIMIT 10;
```

### Telegram мониторинг
- ✅ Отчёты после каждого запуска парсера
- ✅ Алерты при ошибках (cooldown 30 минут)
- ✅ Health check уведомления

### Частые проблемы

**1. Парсер возвращает 0 матчей**
```bash
# Проверить .env или GitHub Secrets
ODDS_API_KEY=...        # для the-odds-api.com
PROXY_URL=...           # для 1xBet (гео-блок РФ)

# Проверить логи
python -m backend.parsers.leonbets_parser  # тестовый запуск
```

**2. Ошибки Redis/Supabase**
```bash
# Health check
python -m backend.health_check

# Проверить переменные окружения
echo $UPSTASH_REDIS_URL
echo $SUPABASE_URL
```

**3. GitHub Actions не запускается**
- Settings → Actions → General → Enable
- Проверить Secrets → Actions
- Проверить workflow статус: Actions → Update Matches

---

## 📖 Дополнительные файлы

| Файл | Описание |
|------|----------|
| `README.md` | Основная документация |
| `ARCHITECTURE.md` | Детальная схема архитектуры |
| `DEPLOYMENT.md` | Инструкция по развёртыванию |
| `QUICK_START.md` | Быстрый старт |
| `CHANGELOG.md` | История изменений |
| `DEPLOY_INSTRUCTIONS.md` | Пошаговая инструкция деплоя |
| `NOTES.md` | Заметки разработчика (статус парсеров, API детали) |
| `OPTIMIZATION_GUIDE.txt` | Руководство по оптимизации |
| `OPTIMIZATIONS_APPLIED.txt` | Применённые улучшения |
| `QWEN.md` | Этот файл (контекст для AI-ассистента) |

---

## 📊 Статус парсеров (v2.3 — март 2026, SOCKS5 прокси)

| Парсер | Статус | Матчей | Примечание |
|--------|--------|--------|------------|
| **Leonbets** | ✅ | ~2540 | Основной источник (95% матчей) |
| **ApiFootball** | ⚠️ | 0 | Rate limit исчерпан (429) |
| **1xBet** | ⚠️ | 0 | Прокси не работает для 1xBet (IP не в РФ) |
| **OddsAPI.io** | ⚠️ | 0 | Лимит исчерпан (429) |
| **the-odds-api.com** | ⚠️ | 0 | 401 Unauthorized (нет ключа) |
| **Pinnacle** | ❌ | 0 | 410 Gone (API недоступен) |

**Итого:** ~2540 матчей (Leonbets + завершённые счёты)

### 🎯 Оптимизация бесплатных лимитов (v2.2)

```yaml
OddsAPI.io:
  - IO_SPORTS: 2 (football, basketball)
  - IO_MAX_EVENTS_PER_SPORT: 25 (было 60)
  - Потребление: 50 запросов/день (вместо 180)

the-odds-api.com:
  - Лиги: 3 (Champions League, EPL, La Liga)
  - Потребление: ~45 запросов/месяц (вместо 150)

ApiFootball:
  - DAYS_AHEAD: 2 (было 3)
  - Лиги: 7 (добавлена РПЛ, удалены второстепенные)
  - Потребление: ~35 запросов/день (вместо 50)

GitHub Actions:
  - Расписание: 3 раза в день (09:00, 17:00, 22:00 MSK)
  - При превышении лимитов: уменьшить до 2 раз
```

### 🔧 Прокси (SOCKS5)

**Конфигурация:**
```env
PROXY_ENABLED=true
PROXY_URL=socks5://LNbHRm:tHCxnE@45.81.77.14:8000
```

**Статус:**
- ✅ Прокси работает (IP: 45.81.77.14)
- ❌ 1xBet недоступен (IP не в России или заблокирован)
- ✅ Leonbets работает без прокси

**Тестирование:**
```bash
# Проверка прокси
python test_user_proxy.py

# Проверка 1xBet через прокси
python test_1xbet_proxy.py
```

**Решение:**
- Купить российский SOCKS5 прокси (proxy6.net, proxy-seller.ru)
- Или использовать HTTP прокси с российским IP

### 📄 Документация

- **PROXY_SETUP.md** — подробная инструкция по настройке прокси и оптимизации лимитов
- **backend/utils/free_proxy_fetcher.py** — скрипт для автоматического поиска бесплатных прокси

---

## 🔮 Возможные улучшения

### Приоритет 1 (данные)
1. **Настроить ODDS_API_KEY** — +60-100 матчей из топ-лиг (5 минут)
   - Получить: https://the-odds-api.com/api-keys/
   - Добавить в GitHub Secrets: `ODDS_API_KEY=sk_...`

2. **Купить прокси для 1xBet** — +5000 матчей (~50₽/месяц)
   - Сервисы: proxy6.net, proxy-sale.com, proxy-seller.ru
   - Формат: `http://login:password@ip:port`
   - Добавить в GitHub Secrets: `PROXY_URL=...`

3. **Исследовать Pinnacle API** — проверить актуальный эндпоинт

### Приоритет 2 (UX)
4. **Пагинация на frontend** — при 2500+ матчах
5. **Сравнение коэффициентов** — показывать лучший odds среди букмекеров
6. **История изменений линии** — отслеживание движения коэффициентов

### Приоритет 3 (функциональность)
7. **База данных** — переход с Google Sheets на PostgreSQL/MongoDB
8. **Админ панель** — интерфейс для редактирования матчей
9. **Live обновления** — WebSocket для real-time коэффициентов
10. **Аналитика** — статистика по ставкам, популярные матчи
11. **Авторизация** — личный кабинет пользователя
12. **История ставок** — хранение и отображение прошлых ставок
13. **API** — REST API для сторонних приложений
14. **Мобильное приложение** — React Native / Flutter

---

## 💡 Советы для разработки

### При добавлении нового парсера:
1. Создайте файл `backend/parsers/new_parser.py`
2. Наследуйтесь от `BaseParser`
3. Реализуйте метод `parse()`
4. Добавьте парсер в `run_parsers.py` и `generate_json.py`

### При изменении формата данных:
1. Обновите `backend/api/generate_json.py`
2. Обновите frontend модули (`filters.js`, `ui.js`)
3. Протестируйте на локальных данных

### При изменении схемы БД:
1. Обновите `config/supabase_schema.sql`
2. Выполните миграцию в Supabase SQL Editor
3. Обновите `backend/db/supabase_client.py`

---

_Версия документа: 2.2 | Последнее обновление: 5 марта 2026_

_Статус парсеров: Leonbets ✅ (2500), ApiFootball ✅ (12), OddsAPI.io ⚠️ (limit reached)_

_Оптимизация: v2.2 — бесплатные лимиты настроены (3 API, ~2500 матчей)_
