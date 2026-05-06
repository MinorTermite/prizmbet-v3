# Работа с VPS и QloudHost — Инструкция для Codex

## Данные серверов

### Новый VPS (основной, prizmbet.net)
- **IP:** 103.217.253.13
- **Хостинг:** QloudHost
- **OS:** Ubuntu 22.04
- **SSH:** root / K3wqdpj6fq6y7
- **Домен:** prizmbet.net (DNS уже настроен)
- **Панель управления:** https://my.qloudhost.com (MAXBEAUBIS@proton.me / BacYtu%655)
- **Virtualizor:** http://103.217.253.13:4082 (или через QloudHost panel)

### Старый VPS (резервный, до 21.04.2026)
- **IP:** 213.165.38.210
- **Хостинг:** aeza.net (my.aeza.net)
- **OS:** Ubuntu 22.04
- **Тариф:** NLs-1 (1 core, 2GB RAM, 30GB SSD)

---

## Подключение к новому VPS

```bash
ssh root@103.217.253.13
# пароль: K3wqdpj6fq6y7
```

### Если SSH не работает (fail2ban бан)

Слишком много неверных попыток блокирует IP на ~1 час. Нужно подождать или использовать VNC через Virtualizor:
1. Войти на https://my.qloudhost.com
2. Services → My Services → VPS 103.217.253.13
3. Login to Virtualizor → VNC Console

Альтернатива — параметр `-o ConnectTimeout=15` и подождать снятия бана.

---

## SSH через Python Paramiko (надёжнее на Windows)

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('103.217.253.13', username='root', password='K3wqdpj6fq6y7', timeout=15)

stdin, stdout, stderr = client.exec_command('echo OK && uname -a')
print(stdout.read().decode())
client.close()
```

---

## Деплой на новый VPS

Полные инструкции в файле `CODEX_DEPLOY_NEW_VPS.md`.

Краткая последовательность:
```bash
# 1. Обновить ОС
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx redis-server

# 2. Клонировать репозиторий
cd /root && git clone https://github.com/MinorTermite/prizmbet-v3.git && cd prizmbet-v3

# 3. Создать .env (см. CODEX_DEPLOY_NEW_VPS.md шаг 4)

# 4. Установить зависимости
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 5. Настроить systemd сервис (см. CODEX_DEPLOY_NEW_VPS.md шаг 6)

# 6. Настроить nginx + SSL (см. CODEX_DEPLOY_NEW_VPS.md шаги 7-8)
```

---

## Управление сервисом на VPS

```bash
# Статус
systemctl status prizmbet

# Перезапуск
systemctl restart prizmbet

# Логи
journalctl -u prizmbet -f --no-pager -n 50

# Деплой обновления
cd /root/prizmbet-v3 && git pull && systemctl restart prizmbet
```

---

## DNS — Porkbun API

Домен `prizmbet.net` управляется через Porkbun.

**API ключи:**
- `apikey`: pk1_50bad893...
- `secretapikey`: sk1_c2e52830a79cf74c867d14b294004719490c50e76413c320fb8421faf5ea858a

**DNS уже настроен:**
- `prizmbet.net` → `103.217.253.13` ✅
- `www.prizmbet.net` → `103.217.253.13` ✅

**Проверить DNS:**
```bash
nslookup prizmbet.net
# или
curl -s https://api.porkbun.com/api/json/v3/dns/retrieve/prizmbet.net \
  -d '{"apikey":"pk1_50bad893...","secretapikey":"sk1_c2e52830..."}'
```

---

## Supabase

- **URL:** https://gvyhjqqhzyhgbbrfrbat.supabase.co
- **Project ID:** gvyhjqqhzyhgbbrfrbat
- **Dashboard:** https://supabase.com/dashboard/project/gvyhjqqhzyhgbbrfrbat
- **Key (service_role):** eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd2eWhqcXFoenloZ2JicmZyYmF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzE4MTUzMiwiZXhwIjoyMDg4NzU3NTMyfQ.lM2MtTp4yurz5jfIFmcZKoH7qY6T9OX0-ZmuWhHorTU

**Применить SQL миграцию:**
1. Открыть Dashboard → SQL Editor
2. Вставить SQL из `supabase/migrations/*.sql`
3. Run

---

## GitHub

- **Репозиторий:** https://github.com/MinorTermite/prizmbet-v3
- **Основная ветка:** main

**Деплой после изменений:**
```bash
# Локально:
git add -A && git commit -m "description" && git push origin main

# На сервере:
cd /root/prizmbet-v3 && git pull && systemctl restart prizmbet
```

---

## Структура проекта

```
prizmbet-v3/
├── backend/
│   ├── main.py              # Точка входа (aiohttp сервер, порт 8081)
│   ├── api/
│   │   └── bet_intents_api.py  # REST API для ставок
│   ├── db/
│   │   └── supabase_client.py  # Supabase клиент
│   └── parsers/             # Парсеры матчей (1xBet, LeonBets)
├── frontend/
│   ├── index.html
│   └── js/modules/
│       ├── bet_slip.js      # Купон ставки
│       ├── payment_rails.js # Платёжные рельсы (PRIZM, USDT-TRC20)
│       └── ...
├── supabase/migrations/     # SQL миграции
├── .env                     # Env vars (НЕ в git)
└── requirements.txt
```

---

## Важные порты

| Порт | Сервис |
|------|--------|
| 22   | SSH |
| 80   | HTTP (nginx → перенаправляет на HTTPS) |
| 443  | HTTPS (nginx → proxy → 8081) |
| 8081 | Backend (aiohttp, только localhost) |

---

## Типичные проблемы

### SSH Permission denied
- Неверный пароль → проверить актуальный пароль в тикете QloudHost
- fail2ban → подождать 1 час

### Сайт не открывается
```bash
systemctl status prizmbet   # бэкенд упал?
systemctl status nginx      # nginx не работает?
curl http://localhost:8081/health  # бэкенд отвечает?
journalctl -u prizmbet -n 30  # смотреть логи
```

### SSL не работает
```bash
certbot renew --dry-run
certbot --nginx -d prizmbet.net -d www.prizmbet.net
```

### git pull конфликты
```bash
git stash && git pull && git stash pop
# или
git fetch origin && git reset --hard origin/main
```
