#!/bin/bash
# PrizmBet watchdog — checks service health, sends Telegram alert on failure
BOT_TOKEN="8450166145:AAGtA0n--gPgK9mW24TQiKjZRjlHnx_Us9o"
CHAT_ID="984705599"
LOCK_FILE="/tmp/prizmbet_watchdog.lock"

# Prevent overlapping runs
if [ -f "$LOCK_FILE" ]; then
    exit 0
fi
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

send_alert() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="${CHAT_ID}" \
        -d "text=${msg}" \
        -d parse_mode="HTML" > /dev/null 2>&1
}

# Check systemd service
if ! systemctl is-active --quiet prizmbet; then
    send_alert "⚠️ <b>PrizmBet DOWN</b>
Service is not active.
Attempting restart..."
    systemctl restart prizmbet
    sleep 8
    if systemctl is-active --quiet prizmbet; then
        send_alert "✅ <b>PrizmBet RECOVERED</b>
Service restarted successfully."
    else
        send_alert "🔴 <b>PrizmBet CRITICAL</b>
Restart failed!"
    fi
    exit 1
fi

# Check HTTP response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8081/index.html 2>/dev/null)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    send_alert "⚠️ <b>PrizmBet HTTP ERROR</b>
HTTP status: ${HTTP_CODE}
Attempting restart..."
    systemctl restart prizmbet
    sleep 8
    HTTP_RETRY=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8081/index.html 2>/dev/null)
    if [ "$HTTP_RETRY" = "200" ] || [ "$HTTP_RETRY" = "302" ]; then
        send_alert "✅ <b>PrizmBet RECOVERED</b>
Service restarted after HTTP error."
    fi
fi
