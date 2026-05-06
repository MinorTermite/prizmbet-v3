# USDT TRC-20 Multi-Currency Migration — Инструкция для Codex

## Цель

Добавить поддержку `payment_currency` (PRIZM / USDT-TRC20) в:
1. Таблицы Supabase (`bet_intents`, `bets`)
2. Backend API (`create_intent`, `create_bet_intent`)
3. Frontend (`payment_rails.js`, `bet_slip.js`)

---

## Шаг 1 — Supabase DB миграция

Создать файл: `supabase/migrations/20260413000100_payment_currency.sql`

```sql
-- Add payment_currency discriminator to bet_intents and bets
-- Supports: 'PRIZM' (default), 'USDT-TRC20'

ALTER TABLE bet_intents
    ADD COLUMN IF NOT EXISTS payment_currency TEXT NOT NULL DEFAULT 'PRIZM'
        CHECK (payment_currency IN ('PRIZM', 'USDT-TRC20'));

ALTER TABLE bets
    ADD COLUMN IF NOT EXISTS payment_currency TEXT NOT NULL DEFAULT 'PRIZM'
        CHECK (payment_currency IN ('PRIZM', 'USDT-TRC20'));

-- Indexes for filtering by currency
CREATE INDEX IF NOT EXISTS idx_bet_intents_currency ON bet_intents(payment_currency);
CREATE INDEX IF NOT EXISTS idx_bets_currency ON bets(payment_currency);

-- Update existing rows to PRIZM
UPDATE bet_intents SET payment_currency = 'PRIZM' WHERE payment_currency IS NULL;
UPDATE bets SET payment_currency = 'PRIZM' WHERE payment_currency IS NULL;
```

**Применить через Supabase MCP или SQL Editor в https://supabase.com/dashboard**

Project ID: `gvyhjqqhzyhgbbrfrbat`

---

## Шаг 2 — payment_rails.js — добавить экспортируемые функции

Файл: `frontend/js/modules/payment_rails.js`

Добавить в конец файла (перед последней строкой или после `initPaymentRails`):

```javascript
/**
 * Returns the payment_currency string for the currently active rail.
 * Used by bet_slip.js to send payment_currency to the backend.
 * PRIZM rail → 'PRIZM'
 * usdt-trc20 → 'USDT-TRC20'
 */
export function getActiveRailCurrency() {
    const rail = getActiveRail();
    if (rail.key === 'usdt-trc20') return 'USDT-TRC20';
    if (rail.key === 'prizm') return 'PRIZM';
    // Default fallback — map by code
    return rail.code === 'USDT' ? 'USDT-TRC20' : 'PRIZM';
}

/**
 * Returns min/max bet limits for the currently active rail.
 * PRIZM: min=1500, max=30000
 * USDT-TRC20: min=1, max=500 (in USDT)
 */
export function getActiveRailLimits() {
    const rail = getActiveRail();
    if (rail.key === 'usdt-trc20') {
        return { minBet: 1, maxBet: 500 };
    }
    // Default PRIZM limits
    return { minBet: 1500, maxBet: 30000 };
}
```

---

## Шаг 3 — bet_slip.js — использовать payment_currency

Файл: `frontend/js/modules/bet_slip.js`

### 3.1 — Обновить import из payment_rails.js

```javascript
// БЫЛО:
import { getActiveRail, getCopyDoneMessage, getCopyMissingMessage, getCouponRailHint, getRailAddress, getTransferChipText, getTransferInstruction, initPaymentRails, renderPaymentRailUI } from './payment_rails.js';

// СТАЛО:
import { getActiveRail, getActiveRailCurrency, getActiveRailLimits, getCopyDoneMessage, getCopyMissingMessage, getCouponRailHint, getRailAddress, getTransferChipText, getTransferInstruction, initPaymentRails, renderPaymentRailUI } from './payment_rails.js';
```

### 3.2 — Заменить статические MIN_BET/MAX_BET на динамические

```javascript
// БЫЛО:
const MIN_BET = 1500;
const MAX_BET = 30000;

// СТАЛО:
const PRIZM_MIN_BET = 1500;
const PRIZM_MAX_BET = 30000;

function getBetLimits() {
    const limits = getActiveRailLimits();
    return {
        minBet: limits.minBet || PRIZM_MIN_BET,
        maxBet: limits.maxBet || PRIZM_MAX_BET,
    };
}
```

### 3.3 — Везде где используется MIN_BET и MAX_BET заменить на getBetLimits()

Найти все вхождения `MIN_BET` и `MAX_BET` в функциях валидации ставки:

```javascript
// Пример замены:
// БЫЛО:
if (amount < MIN_BET || amount > MAX_BET) { ... }

// СТАЛО:
const { minBet, maxBet } = getBetLimits();
if (amount < minBet || amount > maxBet) { ... }
```

### 3.4 — Добавить payment_currency в POST /api/intents

```javascript
// Найти в функции создания интента (обычно fetch('/api/intents', { method: 'POST', body: ... }))
// БЫЛО:
body: JSON.stringify({
    match_id: ...,
    outcome: ...,
    sender_wallet: ...,
})

// СТАЛО:
body: JSON.stringify({
    match_id: ...,
    outcome: ...,
    sender_wallet: ...,
    payment_currency: getActiveRailCurrency(),
})
```

### 3.5 — Добавить payment_currency в buildLocalIntent()

```javascript
// Найти функцию buildLocalIntent или аналог, которая строит локальный объект интента
// Добавить в return:
payment_currency: getActiveRailCurrency(),
```

---

## Шаг 4 — Backend — принять payment_currency в create_intent

Файл: `backend/api/bet_intents_api.py`

### 4.1 — Добавить VALID_CURRENCIES константу вверху файла

```python
VALID_CURRENCIES = {'PRIZM', 'USDT-TRC20'}
```

### 4.2 — Распарсить payment_currency в create_intent

```python
async def create_intent(request: web.Request) -> web.Response:
    ...
    payload = await request.json()
    match_id = str(payload.get("match_id") or "").strip()
    outcome = str(payload.get("outcome") or "").strip().upper()
    sender_wallet = str(payload.get("sender_wallet") or "").strip().upper()
    # NEW:
    payment_currency = str(payload.get("payment_currency") or "PRIZM").strip().upper()
    if payment_currency not in VALID_CURRENCIES:
        payment_currency = "PRIZM"
    ...
```

### 4.3 — Передать payment_currency в db.create_bet_intent

```python
await db.create_bet_intent(
    intent_hash=intent_hash,
    match_id=match_id,
    sender_wallet=sender_wallet,
    outcome=outcome,
    odds_fixed=odds,
    expires_at=expires_at,
    payment_currency=payment_currency,   # NEW
)
```

### 4.4 — Вернуть payment_currency в ответе

```python
intent = {
    "intent_hash": intent_hash,
    "odds_fixed": odds,
    "expires_at": expires_at,
    "match_id": match_id,
    "sender_wallet": sender_wallet,
    "payment_currency": payment_currency,   # NEW
}
```

---

## Шаг 5 — DB layer — добавить payment_currency в create_bet_intent

Файл: `backend/db/supabase_client.py`

```python
async def create_bet_intent(
    self,
    intent_hash: str,
    match_id: str,
    sender_wallet: str,
    outcome: str,
    odds_fixed: float,
    expires_at: str | None = None,
    payment_currency: str = "PRIZM",     # NEW parameter
):
    if not self.initialized:
        return None
    payload = {
        "intent_hash": intent_hash,
        "match_id": str(match_id),
        "sender_wallet": sender_wallet,
        "outcome": outcome,
        "odds_fixed": round(float(odds_fixed), 2),
        "payment_currency": payment_currency,   # NEW
    }
    if expires_at:
        payload["expires_at"] = expires_at
    return self.client.table("bet_intents").insert(payload).execute().data
```

---

## Порядок применения

1. Применить SQL миграцию (Шаг 1) — через Supabase Dashboard → SQL Editor
2. Обновить `payment_rails.js` (Шаг 2)
3. Обновить `bet_slip.js` (Шаг 3)
4. Обновить `bet_intents_api.py` (Шаг 4)
5. Обновить `supabase_client.py` (Шаг 5)
6. Задеплоить на сервер (`git push`, затем `systemctl restart prizmbet` на VPS)
7. Проверить: создать интент через UI с выбранным USDT-TRC20 рельсом, убедиться что в Supabase → bet_intents появляется `payment_currency = 'USDT-TRC20'`

---

## Supabase проект

- **URL:** https://gvyhjqqhzyhgbbrfrbat.supabase.co
- **Project ID:** gvyhjqqhzyhgbbrfrbat
- **Dashboard:** https://supabase.com/dashboard/project/gvyhjqqhzyhgbbrfrbat/editor
