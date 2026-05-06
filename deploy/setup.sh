#!/bin/bash
# PrizmBet v3 hardened VPS setup.
# Run as root on Ubuntu 22.04+:
#   bash deploy/setup.sh your-domain.com
set -euo pipefail

APP_DIR="/opt/prizmbet"
APP_USER="prizmbet"
REPO="${PRIZMBET_REPO:-https://github.com/MinorTermite/prizmbet-v3.git}"
DOMAIN="${1:-}"
NGINX_SERVER_NAME="${DOMAIN:-_}"

echo "=== PrizmBet v3 hardened setup ==="

echo "[1/9] Installing system packages..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    ca-certificates curl git nginx python3 python3-pip python3-venv \
    ufw fail2ban unattended-upgrades

echo "[2/9] Applying OS firewall baseline..."
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

echo "[3/9] Creating app user..."
id -u "$APP_USER" >/dev/null 2>&1 || useradd -r -m -s /usr/sbin/nologin "$APP_USER"

echo "[4/9] Fetching repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git pull --ff-only
else
    rm -rf "$APP_DIR"
    git clone "$REPO" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 750 "$APP_DIR"

echo "[5/9] Installing Python dependencies..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" venv/bin/pip install -q --upgrade pip
sudo -u "$APP_USER" venv/bin/pip install -q -r requirements.txt

echo "[6/9] Preparing environment file..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
fi

if [ -n "$DOMAIN" ]; then
    if grep -q '^ADMIN_CORS_ORIGIN=' "$APP_DIR/.env"; then
        sed -i "s|^ADMIN_CORS_ORIGIN=.*|ADMIN_CORS_ORIGIN=https://${DOMAIN}|" "$APP_DIR/.env"
    else
        echo "ADMIN_CORS_ORIGIN=https://${DOMAIN}" >> "$APP_DIR/.env"
    fi
fi

echo "[7/9] Installing hardened systemd service..."
cat > /etc/systemd/system/prizmbet.service << 'EOF'
[Unit]
Description=PrizmBet v3 Backend
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=prizmbet
Group=prizmbet
WorkingDirectory=/opt/prizmbet
EnvironmentFile=/opt/prizmbet/.env
Environment=API_HOST=127.0.0.1
Environment=API_PORT=8081
ExecStart=/opt/prizmbet/venv/bin/python -m backend.main
Restart=always
RestartSec=3
TimeoutStopSec=20
StandardOutput=journal
StandardError=journal
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/prizmbet
CapabilityBoundingSet=
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
LockPersonality=true
MemoryDenyWriteExecute=true
LimitNOFILE=65535
TasksMax=256
MemoryMax=768M

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prizmbet

echo "[8/9] Installing nginx rate limits and reverse proxy..."
cat > /etc/nginx/conf.d/prizmbet-limits.conf << 'EOF'
server_tokens off;
limit_req_zone $binary_remote_addr zone=prizmbet_site:20m rate=30r/s;
limit_req_zone $binary_remote_addr zone=prizmbet_api:20m rate=12r/s;
limit_req_zone $binary_remote_addr zone=prizmbet_status:20m rate=6r/s;
limit_req_zone $binary_remote_addr zone=prizmbet_login:10m rate=1r/s;
limit_conn_zone $binary_remote_addr zone=prizmbet_conn:20m;
EOF

cat > /etc/nginx/sites-available/prizmbet << NGINX
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    client_max_body_size 256k;
    client_body_timeout 10s;
    client_header_timeout 10s;
    keepalive_timeout 15s;
    send_timeout 15s;
    limit_conn prizmbet_conn 40;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "frame-ancestors 'none'; base-uri 'self'; object-src 'none'" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_connect_timeout 5s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;

    location = /api/admin/login {
        limit_req zone=prizmbet_login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8081;
    }

    location ~ ^/api/(intents/|bet-status/|wallets/.*/dashboard) {
        limit_req zone=prizmbet_status burst=12 nodelay;
        proxy_pass http://127.0.0.1:8081;
    }

    location /api/ {
        limit_req zone=prizmbet_api burst=24 nodelay;
        proxy_pass http://127.0.0.1:8081;
    }

    location / {
        limit_req zone=prizmbet_site burst=80 nodelay;
        proxy_pass http://127.0.0.1:8081;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/prizmbet /etc/nginx/sites-enabled/prizmbet
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "[9/9] Installing fail2ban jail..."
cat > /etc/fail2ban/filter.d/prizmbet-nginx-limit.conf << 'EOF'
[Definition]
failregex = limiting requests, excess:.* by zone "prizmbet_.*", client: <HOST>,
ignoreregex =
EOF

cat > /etc/fail2ban/jail.d/prizmbet.conf << 'EOF'
[prizmbet-nginx-limit]
enabled = true
filter = prizmbet-nginx-limit
logpath = /var/log/nginx/error.log
maxretry = 30
findtime = 120
bantime = 3600
EOF

systemctl enable --now fail2ban
systemctl restart fail2ban

echo "=== Setup complete ==="
echo "Edit secrets:       nano /opt/prizmbet/.env"
echo "Start service:      systemctl start prizmbet"
echo "Check service:      systemctl status prizmbet --no-pager -l"
echo "Check logs:         journalctl -u prizmbet -f"
echo "Important: put Cloudflare/WAF in front of the VPS and do not expose 8081 publicly."
