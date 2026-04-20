#!/usr/bin/env bash
# PrizmBet v3 — performance deploy script
# Run from /root/prizmbet-v3: bash deploy.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== [1/4] env vars ==="
grep -q '^LEONBETS_MAX_FETCH=' .env || echo 'LEONBETS_MAX_FETCH=500' >> .env
grep -q '^LEONBETS_BATCH='      .env || echo 'LEONBETS_BATCH=20'     >> .env
grep -q '^ENABLE_XBET='         .env || echo 'ENABLE_XBET=true'      >> .env
echo "LEONBETS_MAX_FETCH=$(grep '^LEONBETS_MAX_FETCH=' .env | cut -d= -f2)"
echo "LEONBETS_BATCH=$(grep '^LEONBETS_BATCH=' .env | cut -d= -f2)"

echo "=== [2/4] nginx gzip + cache headers ==="
NGINX_CONF=$(grep -rl "server_name.*prizmbet" /etc/nginx/sites-enabled/ 2>/dev/null | head -1)
if [ -z "$NGINX_CONF" ]; then
    NGINX_CONF=$(grep -rl "prizmbet" /etc/nginx/conf.d/ 2>/dev/null | head -1)
fi
if [ -z "$NGINX_CONF" ]; then
    echo "WARN: nginx config not found, skipping gzip patch"
else
    echo "nginx config: $NGINX_CONF"
    cp "$NGINX_CONF" "${NGINX_CONF}.bak-$(date +%s)"
    if grep -q "gzip on" "$NGINX_CONF"; then
        echo "gzip already enabled, skipping"
    else
        python3 - "$NGINX_CONF" <<'PYEOF'
import sys, re
path = sys.argv[1]
with open(path) as f:
    text = f.read()

insert = """
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types application/json text/css application/javascript text/plain;

    location ~* \\.json$ { add_header Cache-Control "public, max-age=30"; }
    location ~* \\.(css|js)$ { add_header Cache-Control "public, max-age=3600"; }
"""

# Insert after the first server_name line that mentions prizmbet
new_text = re.sub(
    r'(server_name[^\n]*prizmbet[^\n]*;)',
    r'\1' + insert,
    text, count=1
)
with open(path, 'w') as f:
    f.write(new_text)
print("gzip + cache headers injected")
PYEOF
    fi
    nginx -t && systemctl reload nginx && echo "nginx reloaded OK"
fi

echo "=== [3/4] restart prizmbet ==="
systemctl restart prizmbet
sleep 2

echo "=== [4/4] status ==="
systemctl is-active prizmbet && echo "prizmbet: RUNNING" || echo "prizmbet: FAILED"
journalctl -u prizmbet -n 10 --no-pager

echo ""
echo "=== DEPLOY OK ==="
echo "Leonbets cap: $(grep '^LEONBETS_MAX_FETCH=' .env | cut -d= -f2) events"
