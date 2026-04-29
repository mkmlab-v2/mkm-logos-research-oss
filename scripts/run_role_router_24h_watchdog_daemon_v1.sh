#!/usr/bin/env bash
set -euo pipefail

# Role-router 24h watchdog daemon helper (SSH/Linux).
# Usage:
#   bash scripts/run_role_router_24h_watchdog_daemon_v1.sh nohup
#   bash scripts/run_role_router_24h_watchdog_daemon_v1.sh tmux
#   bash scripts/run_role_router_24h_watchdog_daemon_v1.sh stop
#   bash scripts/run_role_router_24h_watchdog_daemon_v1.sh status

MODE="${1:-nohup}"
ROOT_DIR="${ROOT_DIR:-$PWD}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/reports}"
WATCHDOG_LOG="${WATCHDOG_LOG:-$LOG_DIR/role_router_24h_watchdog.log}"
JSONL_LOG="${JSONL_LOG:-$LOG_DIR/role_router_24h_watchdog_log.jsonl}"
PID_FILE="${PID_FILE:-$LOG_DIR/role_router_24h_watchdog.pid}"
TMUX_SESSION="${TMUX_SESSION:-role-router-watchdog}"
OBSERVER_ENABLED="${OBSERVER_ENABLED:-1}"
OBSERVER_LOG="${OBSERVER_LOG:-$LOG_DIR/role_router_first30m_observer.log}"

CMD=(
  py "scripts/run_role_router_24h_watchdog_v1.py"
  --duration-hours 24
  --poll-seconds 300
  --auto-rollback
  --min-candidate-days 20
  --log-jsonl "$JSONL_LOG"
)

mkdir -p "$LOG_DIR"

run_first30m_observer() {
  if [[ "$OBSERVER_ENABLED" != "1" ]]; then
    echo "first30m observer skipped (OBSERVER_ENABLED=$OBSERVER_ENABLED)"
    return 0
  fi
  echo "running first30m observer smoke (--no-wait)..."
  if py "scripts/run_role_router_first30m_observer_v1.py" --no-wait >"$OBSERVER_LOG" 2>&1; then
    echo "first30m observer done (log=$OBSERVER_LOG)"
  else
    echo "first30m observer failed; continuing watchdog start (log=$OBSERVER_LOG)"
  fi
}

run_nohup() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "watchdog already running (pid=$(cat "$PID_FILE"))"
    return 0
  fi
  run_first30m_observer
  nohup "${CMD[@]}" >"$WATCHDOG_LOG" 2>&1 &
  echo "$!" >"$PID_FILE"
  echo "watchdog started via nohup (pid=$!)"
  echo "tail -f \"$WATCHDOG_LOG\""
}

run_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux not installed; fallback to nohup"
    run_nohup
    return
  fi
  if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "tmux session already exists: $TMUX_SESSION"
    echo "attach: tmux attach -t $TMUX_SESSION"
    return 0
  fi
  run_first30m_observer
  tmux new-session -d -s "$TMUX_SESSION" "cd \"$ROOT_DIR\" && ${CMD[*]} | tee \"$WATCHDOG_LOG\""
  echo "watchdog started in tmux session: $TMUX_SESSION"
  echo "attach: tmux attach -t $TMUX_SESSION"
}

stop_all() {
  if [[ -f "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE" || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      echo "stopped nohup watchdog pid=$pid"
    fi
    rm -f "$PID_FILE"
  fi
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    tmux kill-session -t "$TMUX_SESSION" || true
    echo "stopped tmux session: $TMUX_SESSION"
  fi
}

status_all() {
  running=false
  if [[ -f "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE" || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "nohup: running pid=$pid"
      running=true
    else
      echo "nohup: not running (stale pid file)"
    fi
  else
    echo "nohup: not running"
  fi

  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "tmux: running session=$TMUX_SESSION"
    running=true
  else
    echo "tmux: not running"
  fi

  if [[ "$running" = false ]]; then
    exit 1
  fi
}

case "$MODE" in
  nohup) run_nohup ;;
  tmux) run_tmux ;;
  stop) stop_all ;;
  status) status_all ;;
  *)
    echo "unknown mode: $MODE"
    echo "usage: $0 [nohup|tmux|stop|status]"
    exit 2
    ;;
esac
