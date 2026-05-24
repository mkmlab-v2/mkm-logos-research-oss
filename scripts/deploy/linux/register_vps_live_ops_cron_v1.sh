#!/usr/bin/env bash
set -euo pipefail
# Register VPS crons for live ops: Binance export/sync + Aroon signal webhook.
DESTINY_ROOT="${DESTINY_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
BT="$DESTINY_ROOT/projects/bitcoin-trading"
EXPORT_TASK="bitcoin-binance-export-then-cursor-trade-history"
AROON_TASK="bitcoin-aroon-signal-webhook"
EXPORT_SCHEDULE="${EXPORT_SCHEDULE:-*/30 * * * *}"
AROON_SCHEDULE="${AROON_SCHEDULE:-*/5 * * * *}"
EXPORT_LOG="${EXPORT_LOG:-/var/log/bitcoin_export_then_cursor_trade_history.log}"
AROON_LOG="${AROON_LOG:-/var/log/aroon_signal_webhook.log}"

if [[ ! -f "$BT/scripts/export_binance_fills_to_cursor_trade_history_v1.py" ]]; then
  echo "[ERROR] missing $BT/scripts/export_binance_fills_to_cursor_trade_history_v1.py" >&2
  exit 2
fi
if [[ ! -f "$BT/scripts/dispatch_aroon_signal_webhook_v1.py" ]]; then
  echo "[WARN] missing dispatch_aroon_signal_webhook_v1.py on VPS — git pull destiny root first" >&2
fi

EXPORT_CMD="cd \"$BT\" && python3 scripts/export_binance_fills_to_cursor_trade_history_v1.py --hours 24 --run-sync --sync-hours 24 >> \"$EXPORT_LOG\" 2>&1"
AROON_CMD="cd \"$DESTINY_ROOT\" && set -a && [ -f .env ] && . ./.env; set +a && cd \"$BT\" && python3 scripts/dispatch_aroon_signal_webhook_v1.py >> \"$AROON_LOG\" 2>&1"

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$EXPORT_TASK" | grep -v "$AROON_TASK" > "$TMP" || true
echo "$EXPORT_SCHEDULE $EXPORT_CMD # $EXPORT_TASK" >> "$TMP"
echo "$AROON_SCHEDULE $AROON_CMD # $AROON_TASK" >> "$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "[OK] crons registered"
crontab -l | grep -E "$EXPORT_TASK|$AROON_TASK" || true
