#!/bin/bash
# PrizmBet v3 — VPS auto-setup script
# Run as root on a fresh Ubuntu 22.04+ VPS
# Usage: bash setup.sh [your-domain.com]
set -euo pipefail

APP_DIR="/opt/prizmbet"
APP_USER="prizmbet"
REPO="https://github.com/MinorTermite/prizmbet-v3.git"
DOMAIN="${1:-}"

echo "=== PrizmBet v3 — VPS Setup ==="

# 1. System packages
echo "[1/7] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git nginx ufw

# 2. Firewall
echo "[2/7] Configuring firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

# 3. Create app user
echo "[3/7] Creating app user..."
id -u "$APP_USER" &>/dev/null || useradd -r -m -s /bin/bash "$APP_USER"

# 4. Clone repo
echo "[4/7] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && git pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 5. Python venv & dependencies
echo "[5/7] Setting up Python environment..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" venv/bin/pip install -q --upgrade pip
sudo -u "$APP_USER" venv/bin/pip install -q aiohttp supabase httpx python-dotenv

# 6. Env file
echo "[6/7] Setting up .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo ">>> EDIT CREDENTIALS: nano /opt/prizmbet/.env"
    echo ""
fi

# 7. Systemd service
echo "[7/7] Installing services..."
cat > /etc/systemd/system/prizmbet.service << 'EOF'
[Unit]
Description=PrizmBet v3 Backend
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=prizmbet
Group=prizmbet
WorkingDirectory=/opt/prizmbet
EnvironmentFile=/opt/prizmbet/.env
ExecStart=/opt/prizmbet/venv/bin/python -m backend.main
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prizmbet

# Nginx reverse proxy
NGINX_SERVER_NAME="${DOMAIN:-_}"
cat > /etc/nginx/sites-available/prizmbet << NGINX
server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/prizmbet /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit credentials:     nano /opt/prizmbet/.env"
echo "  2. Start service:        systemctl start prizmbet"
echo "  3. Check status:         systemctl status prizmbet"
echo "  4. View logs:            journalctl -u prizmbet -f"
if [ -n "$DOMAIN" ]; then
echo "  5. Site:                 http://$DOMAIN"
echo "  6. Operator panel:       http://$DOMAIN/operator.html"
else
echo "  5. Site:                 http://YOUR_IP"
echo "  6. Operator panel:       http://YOUR_IP/operator.html"
fi
echo ""
echo "To add SSL with Cloudflare:"
echo "  - Point your domain DNS to this server IP via Cloudflare"
echo "  - Set SSL mode to 'Flexible' in Cloudflare dashboard"
echo "  - Your site will be available at https://$DOMAIN"
echo ""
