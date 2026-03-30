from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _env_snapshot() -> str:
    keys = ("PYTHONPATH", "PWD", "BIBLE_INSIGHT_COMMAND")
    parts = []
    for key in keys:
        value = os.getenv(key, "")
        parts.append(f"{key}={value if value else '<empty>'}")
    return " ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lightweight interval loop runner for SSH/PM2")
    parser.add_argument("--name", required=True, help="Logical loop name")
    parser.add_argument("--interval-sec", required=True, type=int, help="Interval seconds")
    parser.add_argument("--command", required=True, help="Shell-like command string")
    parser.add_argument("--initial-delay-sec", type=int, default=0, help="Initial startup delay seconds")
    args = parser.parse_args()

    if args.interval_sec < 1:
        print("--interval-sec must be >= 1", file=sys.stderr, flush=True)
        return 2

    if args.initial_delay_sec > 0:
        print(f"[{_utc_now()}] [{args.name}] initial delay {args.initial_delay_sec}s", flush=True)
        time.sleep(args.initial_delay_sec)

    expanded_command = os.path.expandvars(args.command)
    cmd = shlex.split(expanded_command)
    print(f"[{_utc_now()}] [{args.name}] env_snapshot {_env_snapshot()}", flush=True)
    while True:
        started = time.monotonic()
        print(f"[{_utc_now()}] [{args.name}] run_start command={' '.join(cmd)}", flush=True)
        try:
            proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
            print(f"[{_utc_now()}] [{args.name}] run_end exit_code={proc.returncode}", flush=True)
        except Exception as exc:
            print(f"[{_utc_now()}] [{args.name}] run_exception error={exc}", file=sys.stderr, flush=True)

        elapsed = time.monotonic() - started
        sleep_for = max(0, args.interval_sec - int(elapsed))
        if sleep_for > 0:
            time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
