# CODEX: PrizmBet Gamification — Инструкция для агента

## Контекст проекта
- Проект: PrizmBet v3 — букмекерская платформа на криптовалюте PRIZM
- Stack: Python aiohttp backend, Vanilla JS frontend, Supabase (Postgres)
- Supabase project ID: `gvyhjqqhzyhgbbrfrbat`
- Git remote: GitHub (MinorTermite)
- Основная ветка: `main`

## Что уже сделано (не трогать)
- ✅ Все финансовые таблицы с RLS и immutable триггерами
- ✅ Circuit breaker в auto_payout.py
- ✅ Wallet sweep (hot→cold) в wallet_sweep.py
- ✅ Шапка сайта: SVG lockup с inline иконкой
- ✅ Hero CTA, новый footer, кнопка "Показать все лиги"
- ✅ LEAGUES_PER_PAGE = 15
- ✅ SW v43, кэш prizmbet-header-lockup.svg

## Задача: Реализовать геймификационный слой

### Шаг 1 — Supabase миграции

Создать через `mcp__24320b80-3075-40e6-9266-4cab2d6c0fda__apply_migration`:

```sql
-- 1. player_profiles
CREATE TABLE player_profiles (
  wallet TEXT PRIMARY KEY,
  level INT NOT NULL DEFAULT 1,
  level_name TEXT NOT NULL DEFAULT 'НАБЛЮДАТЕЛЬ',
  total_won_prizm NUMERIC(20,2) NOT NULL DEFAULT 0,
  total_bet_turnover NUMERIC(20,2) NOT NULL DEFAULT 0,
  roulette_spins INT NOT NULL DEFAULT 0,
  raffle_tokens INT NOT NULL DEFAULT 0,
  prizmaster_badge BOOL NOT NULL DEFAULT false,
  prizmaster_level INT,  -- на каком уровне получен последний значок
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. player_quests
CREATE TABLE player_quests (
  id BIGSERIAL PRIMARY KEY,
  wallet TEXT NOT NULL,
  quest_id TEXT NOT NULL,
  level_unlocked INT NOT NULL DEFAULT 1,
  progress NUMERIC(20,2) NOT NULL DEFAULT 0,
  target NUMERIC(20,2) NOT NULL,
  times_required INT NOT NULL DEFAULT 1,
  times_completed INT NOT NULL DEFAULT 0,
  completed BOOL NOT NULL DEFAULT false,
  completed_at TIMESTAMPTZ,
  reward_claimed BOOL NOT NULL DEFAULT false,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_player_quests_unique ON player_quests(wallet, quest_id, level_unlocked);

-- 3. player_bonuses
CREATE TABLE player_bonuses (
  id BIGSERIAL PRIMARY KEY,
  wallet TEXT NOT NULL,
  bonus_type TEXT NOT NULL,  -- 'pct_win', 'cashback', 'roulette_spins', 'raffle_token', 'freespins'
  bonus_key TEXT NOT NULL,   -- 'temp_millionaire', 'riskoviy_cashback', 'prizmaster', etc.
  value NUMERIC(10,4) NOT NULL DEFAULT 0,
  expires_at TIMESTAMPTZ,
  activated_at TIMESTAMPTZ,
  activated BOOL NOT NULL DEFAULT false,
  burn_on_level_up BOOL NOT NULL DEFAULT false,
  burned_at TIMESTAMPTZ,
  source TEXT,               -- 'quest', 'roulette', 'top3', 'admin'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. roulette_log
CREATE TABLE roulette_log (
  id BIGSERIAL PRIMARY KEY,
  wallet TEXT NOT NULL,
  event_type TEXT NOT NULL,  -- 'earned', 'spent', 'prize'
  spins_delta INT NOT NULL,
  source TEXT,               -- 'bet:{tx_id}', 'quest:{quest_id}', 'top3'
  prize_type TEXT,
  prize_value TEXT,
  bet_tx_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. raffle_tokens_log
CREATE TABLE raffle_tokens_log (
  id BIGSERIAL PRIMARY KEY,
  wallet TEXT NOT NULL,
  delta INT NOT NULL,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. raffles
CREATE TABLE raffles (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  questions JSONB NOT NULL DEFAULT '[]',
  starts_at TIMESTAMPTZ,
  ends_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','active','completed','cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. raffle_entries
CREATE TABLE raffle_entries (
  id BIGSERIAL PRIMARY KEY,
  raffle_id BIGINT NOT NULL REFERENCES raffles(id),
  wallet TEXT NOT NULL,
  answers JSONB NOT NULL DEFAULT '[]',
  score INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(raffle_id, wallet)
);

-- 8. weekly_leaderboard
CREATE TABLE weekly_leaderboard (
  id BIGSERIAL PRIMARY KEY,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  wallet TEXT NOT NULL,
  rank INT NOT NULL,
  won_prizm NUMERIC(20,2) NOT NULL DEFAULT 0,
  prize_distributed BOOL NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(week_start, wallet)
);
```

Включить RLS на всех (service_role bypass, deny public):
```sql
ALTER TABLE player_profiles ENABLE ROW LEVEL SECURITY;
-- + остальные таблицы аналогично
-- + политики deny для anon/authenticated
```

### Шаг 2 — Backend: gamification.py

Создать `backend/bot/gamification.py`:

```python
# Вызывается после каждого mark_bet_paid() и settle_bet()
async def on_bet_settled(wallet: str, bet_tx_id: str, amount_prizm: float,
                         odds: float, won: bool, league: str, sport: str):
    """
    - Если won=True: прибавить amount_prizm * odds к total_won_prizm
    - Всегда: прибавить amount_prizm к total_bet_turnover
    - Начислить roulette_spins: floor(amount_prizm / 1500)
    - Обновить прогресс квестов
    - Проверить повышение уровня
    """

async def check_level_up(wallet: str) -> bool:
    """Проверить условия уровня, повысить если выполнены, сжечь бонусы burn_on_level_up"""

async def spin_roulette(wallet: str, spins: int) -> list[dict]:
    """Прокрутить рулетку N раз, начислить призы"""
    # Призы с весами (не показывать игрокам):
    # - 'spins_15': weight=1/150
    # - 'cashback_20': weight=1/300
    # - 'win_boost_50': weight=1/1000
    # - 'temp_millionaire': weight=1/700
    # - 'raffle_token': weight=1/1500
    # - 'nothing': остаток
```

### Шаг 3 — Frontend: cabinet_v2.js

Новый модуль `frontend/js/modules/cabinet_v2.js`:
- Загружает `/api/player/{wallet}` (GET)
- Рендерит: уровень + прогресс-бар, счётчик PRIZM, задания (текущий уровень + превью следующего)
- Медали: клик → модалка с описанием бонуса
- Персонаж: img зависит от уровня (level1.svg ... level11.svg)

### Шаг 4 — API эндпоинты

Добавить в `backend/api/bet_intents_api.py`:

```
GET  /api/player/{wallet}              — профиль, уровень, бонусы, задания
GET  /api/player/{wallet}/quests       — задания с прогрессом
POST /api/player/{wallet}/roulette     — потратить прокруты
GET  /api/leaderboard/weekly           — топ-10 недели
GET  /api/raffles/active               — текущий розыгрыш
POST /api/raffles/{id}/enter           — подать ответы
```

### Шаг 5 — Экспресс-ставки

В `frontend/js/modules/bet_slip.js`:
- Добавить режим "Экспресс" — несколько исходов
- Перемножать коэффициенты, показывать итоговый (cap 100)
- Блокировать добавление 2 исходов с одного матча

В `backend/api/bet_intents_api.py`:
- Поле `bet_type: 'single' | 'express'`
- Поле `legs: [{match_id, outcome, odds}]`
- Валидация: нет дублей match_id, итог_коэфф ≤ 100

### Шаг 6 — UI кабинета

В `frontend/index.html` — кабинет-sheet:
- Вкладки: "Статистика" / "Задания" / "Бонусы" / "Рулетка"
- Персонаж: `<img src="player-level-{N}.svg">` (нужно создать или подобрать)
- Прогресс до следующего уровня: `{current_turnover} / {target_turnover} PRIZM`

---

## Правила реализации

1. **Оборот = только выигранные монеты** (total_won_prizm), ставки не считаются
2. **Одинаковые бонусы не суммируются** — второй ждёт пока первый истечёт
3. **Бонусы burn_on_level_up сгорают** при переходе на новый уровень
4. **Не активированный бонус** сгорает через 1 месяц (expires_at = NOW() + 30 days)
5. **Видимость заданий**: только текущий уровень + следующий (остальное hidden)
6. **Значок НАСТОЯЩЕГО ПРИЗМАЧА** исчезает при переходе на новый уровень (prizmaster_level != current_level)
7. **Шансы рулетки** — не показывать игрокам, только в /rules
8. **service_role** для всех записей в gamification-таблицы

---

## Файлы для изучения перед началом

- `backend/db/supabase_client.py` — паттерны работы с Supabase
- `backend/bot/auto_payout.py` — как вызывать после выплаты
- `backend/bot/v3_settler.py` — где settle происходит
- `frontend/js/modules/history_ui.js` — текущий UI кабинета
- `frontend/js/modules/bet_slip.js` — текущий bet slip (для экспресса)
- `frontend/css/smart-flow.css` — стили (glassmorphism, indigo палитра)
- `frontend/js/modules/i18n.js` — добавлять новые ключи сюда

---

## Ключевые константы уровней

```python
LEVELS = [
    {"level": 1,  "name": "НАБЛЮДАТЕЛЬ",       "turnover": 0,                    "quests": 0},
    {"level": 2,  "name": "НАЧИНАЮЩИЙ ИГРОК",  "turnover": 1_500,                "quests": 1},
    {"level": 3,  "name": "ИГРОК",             "turnover": 100_000,              "quests": 1},
    {"level": 4,  "name": "ОПЫТНЫЙ ИГРОК",     "turnover": 1_000_000,            "quests": 2},
    {"level": 5,  "name": "ИГРАЮЩИЙ ТРЕНЕР",   "turnover": 10_000_000,           "quests": 3},
    {"level": 6,  "name": "НАЧИНАЮЩИЙ ТРЕНЕР", "turnover": 100_000_000,          "quests": 4},
    {"level": 7,  "name": "ТРЕНЕР",            "turnover": 1_000_000_000,        "quests": 5},
    {"level": 8,  "name": "ОПЫТНЫЙ ТРЕНЕР",    "turnover": 10_000_000_000,       "quests": 6},
    {"level": 9,  "name": "СТАРШИЙ ТРЕНЕР",    "turnover": 100_000_000_000,      "quests": 7},
    {"level": 10, "name": "СОВЕТНИК",          "turnover": 1_000_000_000_000,    "quests": 8},
    {"level": 11, "name": "ХРАНИТЕЛЬ ТРАДИЦИЙ","turnover": 10_000_000_000_000,   "quests": 9},
]
```

---

## Порядок коммитов

1. `feat(db): add gamification tables — player_profiles, quests, bonuses, roulette, raffle`
2. `feat(backend): gamification.py — on_bet_settled, check_level_up, spin_roulette`
3. `feat(backend): player API endpoints — GET /api/player/{wallet}, roulette, leaderboard`
4. `feat(frontend): cabinet_v2 — level display, quests, bonuses tabs`
5. `feat(frontend): express bet mode in bet_slip.js`
6. `feat(frontend): roulette UI widget`
