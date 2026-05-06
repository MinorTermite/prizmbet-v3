# Р”РµРїР»РѕР№ PrizmBet v3 РЅР° РЅРѕРІС‹Р№ VPS (103.217.253.13)

## Р”Р°РЅРЅС‹Рµ СЃРµСЂРІРµСЂР°
- **IP:** 103.217.253.13
- **OS:** Ubuntu 22.04
- **User:** root
- **Password:** K3wqdpj6fq6y7
- **Domain:** prizmbet.net (A-Р·Р°РїРёСЃСЊ СѓР¶Рµ СѓРєР°Р·С‹РІР°РµС‚ РЅР° СЌС‚РѕС‚ IP)

---

## Р—Р°РґР°С‡Р°

Р—Р°РґРµРїР»РѕРёС‚СЊ PrizmBet v3 РЅР° РЅРѕРІС‹Р№ VPS СЃ РЅСѓР»СЏ. РЈСЃС‚Р°РЅРѕРІРёС‚СЊ РІСЃРµ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё, РЅР°СЃС‚СЂРѕРёС‚СЊ nginx, SSL, systemd-СЃРµСЂРІРёСЃ.

---

## РЁР°Рі 1 вЂ” РџРѕРґРєР»СЋС‡РµРЅРёРµ Рє СЃРµСЂРІРµСЂСѓ

```bash
ssh root@103.217.253.13
# password: K3wqdpj6fq6y7
```

Р•СЃР»Рё SSH РЅРµРґРѕСЃС‚СѓРїРµРЅ (fail2ban) вЂ” РїРѕРґРѕР¶РґР°С‚СЊ 1 С‡Р°СЃ Рё РїРѕРїСЂРѕР±РѕРІР°С‚СЊ СЃРЅРѕРІР°.

---

## РЁР°Рі 2 вЂ” Р‘Р°Р·РѕРІР°СЏ РїРѕРґРіРѕС‚РѕРІРєР° СЃРµСЂРІРµСЂР°

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx redis-server curl ufw
```

---

## РЁР°Рі 3 вЂ” РљР»РѕРЅРёСЂРѕРІР°РЅРёРµ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ

```bash
cd /root
git clone https://github.com/MinorTermite/prizmbet-v3.git
cd prizmbet-v3
```

---

## РЁР°Рі 4 вЂ” РЎРѕР·РґР°РЅРёРµ .env С„Р°Р№Р»Р°

```bash
cat > /root/prizmbet-v3/.env << 'EOF'
SUPABASE_URL=https://gvyhjqqhzyhgbbrfrbat.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd2eWhqcXFoenloZ2JicmZyYmF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzE4MTUzMiwiZXhwIjoyMDg4NzU3NTMyfQ.lM2MtTp4yurz5jfIFmcZKoH7qY6T9OX0-ZmuWhHorTU
ADMIN_VIEW_KEY=952b207ba5dc40cfb6404e0e6b7f8edd
V3_TELEGRAM_BOT_TOKEN=<rotate-in-botfather>
V3_TELEGRAM_CHAT_ID=984705599
V3_TELEGRAM_CHAT_IDS=984705599
V3_TELEGRAM_MIN_ALERT_PRIZM=1000
SUPER_ADMIN_EMAIL=yatsfe9@gmail.com
SUPER_ADMIN_LOGIN=owner
ODDS_API_KEY=8e7cc59d7c7570ff91dc20eba6deb838
UPSTASH_REDIS_REST_URL=https://innocent-shrimp-80891.upstash.io
UPSTASH_REDIS_REST_TOKEN=gQAAAAAAATv7AAIncDI5YTczYjlhNGRkNzM0OTc5OGRhNDVhNWExYWU1ZTQ3M3AyODA4OTE
EOF
```

---

## РЁР°Рі 5 вЂ” Python РІРёСЂС‚СѓР°Р»СЊРЅРѕРµ РѕРєСЂСѓР¶РµРЅРёРµ Рё Р·Р°РІРёСЃРёРјРѕСЃС‚Рё

```bash
cd /root/prizmbet-v3
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## РЁР°Рі 6 вЂ” Systemd СЃРµСЂРІРёСЃ

```bash
cat > /etc/systemd/system/prizmbet.service << 'EOF'
[Unit]
Description=PrizmBet v3 Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/prizmbet-v3
EnvironmentFile=/root/prizmbet-v3/.env
ExecStart=/root/prizmbet-v3/venv/bin/python backend/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prizmbet
systemctl start prizmbet
systemctl status prizmbet
```

---

## РЁР°Рі 7 вЂ” Nginx РєРѕРЅС„РёРіСѓСЂР°С†РёСЏ

```bash
cat > /etc/nginx/sites-available/prizmbet << 'EOF'
server {
    listen 80;
    server_name prizmbet.net www.prizmbet.net;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}
EOF

ln -sf /etc/nginx/sites-available/prizmbet /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

---

## РЁР°Рі 8 вЂ” SSL СЃРµСЂС‚РёС„РёРєР°С‚ (Let's Encrypt)

```bash
certbot --nginx -d prizmbet.net -d www.prizmbet.net --non-interactive --agree-tos -m yatsfe9@gmail.com
systemctl reload nginx
```

---

## РЁР°Рі 9 вЂ” Firewall

```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable
```

---

## РЁР°Рі 10 вЂ” РџСЂРѕРІРµСЂРєР°

```bash
systemctl status prizmbet
curl -s http://localhost:8081/health
curl -s https://prizmbet.net/health
```

---

## РћР¶РёРґР°РµРјС‹Р№ СЂРµР·СѓР»СЊС‚Р°С‚

- РЎР°Р№С‚ РґРѕСЃС‚СѓРїРµРЅ РїРѕ `https://prizmbet.net`
- Р‘СЌРєРµРЅРґ СЂР°Р±РѕС‚Р°РµС‚ РЅР° РїРѕСЂС‚Сѓ 8081
- SSL СЃРµСЂС‚РёС„РёРєР°С‚ Р°РєС‚РёРІРµРЅ
- РЎРµСЂРІРёСЃ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РїРµСЂРµР·Р°РїСѓСЃРєР°РµС‚СЃСЏ РїСЂРё СЃР±РѕСЏС…

---

## Р’Р°Р¶РЅС‹Рµ Р·Р°РјРµС‚РєРё

- DNS СѓР¶Рµ РЅР°СЃС‚СЂРѕРµРЅ: `prizmbet.net` в†’ `103.217.253.13` вњ…
- РЎС‚Р°СЂС‹Р№ СЃРµСЂРІРµСЂ (213.165.38.210) РїСЂРѕРґРѕР»Р¶Р°РµС‚ СЂР°Р±РѕС‚Р°С‚СЊ РїР°СЂР°Р»Р»РµР»СЊРЅРѕ
- РџРѕСЃР»Рµ СѓСЃРїРµС€РЅРѕРіРѕ РґРµРїР»РѕСЏ вЂ” РѕР±РЅРѕРІРёС‚СЊ APK (WebView URL СЃ IP РЅР° https://prizmbet.net)

