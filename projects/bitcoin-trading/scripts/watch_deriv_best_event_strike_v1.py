#!/usr/bin/env python3
"""
watch_deriv_best_event_strike_v1

Best-event signal watcher:
- Polls run_deriv_best_event_strike_v1.py on an interval
- Executes at most one live strike when signal=true (unless --max-fills > 1)
- Writes append-only journal for audit

Research/ops helper only. Does not modify governance docs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _workspace_root() -> Path:
    here = Path(__file__).resolve()
    if (
        here.parent.name == "scripts"
        and here.parent.parent.name == "bitcoin-trading"
        and here.parents[2].name == "projects"
    ):
        return here.parents[3]
    return here.parents[3] if len(here.parents) > 3 else here.parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    ws = _workspace_root()
    scripts = ws / "projects" / "bitcoin-trading" / "scripts"
    reports = ws / "reports"

    parser = argparse.ArgumentParser(description="Watch best-event signal and strike when true.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--qty", type=float, default=0.001)
    parser.add_argument("--leverage", type=int, default=2)
    parser.add_argument("--interval-sec", type=int, default=300)
    parser.add_argument("--iterations", type=int, default=0, help="0 means infinite loop")
    parser.add_argument("--max-fills", type=int, default=1, help="max live fills before stop")
    parser.add_argument("--mainnet", action="store_true")
    parser.add_argument("--live", action="store_true", help="place real order when signal=true")
    parser.add_argument(
        "--journal-jsonl",
        type=Path,
        default=reports / "deriv_best_event_watch_journal_v1.jsonl",
    )
    args = parser.parse_args()

    if args.qty <= 0:
        raise SystemExit("--qty must be positive")
    if args.leverage <= 0:
        raise SystemExit("--leverage must be positive")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be positive")

    strike_script = scripts / "run_deriv_best_event_strike_v1.py"
    fills = 0
    loops = 0
    args.journal_jsonl.parent.mkdir(parents=True, exist_ok=True)

    while True:
        loops += 1
        cmd = [
            sys.executable,
            str(strike_script),
            "--symbol",
            args.symbol,
            "--qty",
            str(args.qty),
            "--leverage",
            str(args.leverage),
        ]
        if args.mainnet:
            cmd.append("--mainnet")
        if args.live:
            cmd.append("--live")

        proc = _run(cmd)
        row: Dict[str, Any] = {
            "schema": "deriv_best_event_watch_journal_v1",
            "ts_utc": _utc_now(),
            "loop": loops,
            "cmd": cmd,
            "rc": proc.returncode,
            "stdout": (proc.stdout or "")[:2000],
            "stderr": (proc.stderr or "")[:2000],
            "filled_count_total": fills,
        }

        signal = False
        attempted = False
        if proc.returncode == 0 and proc.stdout:
            try:
                payload = json.loads(proc.stdout)
                signal = bool(payload.get("signal"))
                attempted = bool(payload.get("order_attempted"))
            except Exception:
                pass
        if signal and attempted and args.live:
            fills += 1
            row["filled_count_total"] = fills

        with args.journal_jsonl.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

        if args.max_fills > 0 and fills >= args.max_fills:
            break
        if args.iterations > 0 and loops >= args.iterations:
            break
        time.sleep(args.interval_sec)

    print(
        json.dumps(
            {
                "ok": True,
                "loops": loops,
                "fills": fills,
                "journal": str(args.journal_jsonl),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
