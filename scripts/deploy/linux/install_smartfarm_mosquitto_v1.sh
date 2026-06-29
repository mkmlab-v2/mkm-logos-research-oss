#!/usr/bin/env bash
# Install Mosquitto broker for QuBICS MQTT bridge (localhost-only listener).
#
# Usage (on VPS):
#   sudo bash scripts/deploy/linux/install_smartfarm_mosquitto_v1.sh
#   sudo bash scripts/deploy/linux/install_smartfarm_mosquitto_v1.sh --start-subscriber
#
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
START_SUBSCRIBER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start-subscriber)
      START_SUBSCRIBER=1
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y mosquitto mosquitto-clients

CONF_DROP="/etc/mosquitto/conf.d/mkm_smartfarm_local_v1.conf"
cat >"$CONF_DROP" <<'EOF'
# MKM smartfarm pilot — localhost broker for PM2 subscriber (G300 uplink via VPN/tunnel later)
listener 1883 127.0.0.1
allow_anonymous true
EOF

systemctl enable mosquitto
systemctl restart mosquitto
sleep 2

if ! systemctl is-active --quiet mosquitto; then
  echo "mosquitto failed to start" >&2
  systemctl status mosquitto --no-pager || true
  exit 1
fi

if ! mosquitto_pub -h 127.0.0.1 -p 1883 -t 'mkm/smartfarm/health' -m 'ok' -q 1 >/dev/null 2>&1; then
  echo "mosquitto pub smoke failed" >&2
  exit 1
fi

echo "OK: mosquitto listening on 127.0.0.1:1883"

if [[ "$START_SUBSCRIBER" -eq 1 ]]; then
  if [[ ! -d "$REPO_ROOT" ]]; then
    echo "REPO_ROOT not found: $REPO_ROOT" >&2
    exit 2
  fi
  PM2_CONFIG="${REPO_ROOT}/scripts/deploy/linux/pm2_smartfarm_mqtt_subscriber.config.cjs"
  VENV="${REPO_ROOT}/.venv-smartfarm"
  if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
  pip install -q --upgrade pip
  pip install -q paho-mqtt fastapi uvicorn pydantic
  if command -v pm2 >/dev/null 2>&1 && [[ -f "$PM2_CONFIG" ]]; then
    pm2 delete smartfarm-mqtt-subscriber 2>/dev/null || true
    pm2 start "$PM2_CONFIG"
    pm2 save || true
    echo "PM2 smartfarm-mqtt-subscriber started"
  else
    echo "pm2 or config missing — start subscriber manually" >&2
  fi
fi

echo "Done. Field G300 must publish to broker host:port (tunnel/VPN TBD)."
