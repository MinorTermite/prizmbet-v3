#!/bin/bash
# PrizmBet v3 — Pull latest code and restart
set -euo pipefail

cd /opt/prizmbet
sudo -u prizmbet git pull --ff-only
sudo -u prizmbet venv/bin/pip install -q -r requirements.txt 2>/dev/null || true
systemctl restart prizmbet
echo "Updated and restarted. Status:"
systemctl status prizmbet --no-pager -l
