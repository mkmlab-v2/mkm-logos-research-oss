#!/usr/bin/env python3
"""Observe first 30 minutes after submit with timed checkpoints."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ENGINE = ART / "btc_limited_live_engine_input_from_role_router_latest.json"
DEFAULT_WATCHDOG = ROOT / "reports" / "role_router_24h_watchdog_log.jsonl"
DEFAULT_INTENT = ART / "role_router_intent_contract_check_v1_latest.json"
DEFAULT_OUT = ART / "role_router_first30m_observer_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _watchdog_tail(path: Path, limit: int = 3) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _run_intent_check(engine_input: Path) -> tuple[int, dict[str, Any] | None]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_role_router_intent_contract_v1.py"),
        "--engine-input-json",
        str(engine_input),
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    return rc, _read_json(DEFAULT_INTENT)


def _checkpoint_snapshot(name: str, engine_input: Path, watchdog_log: Path) -> dict[str, Any]:
    engine = _read_json(engine_input) or {}
    rc, intent = _run_intent_check(engine_input)
    tail = _watchdog_tail(watchdog_log)
    return {
        "checkpoint": name,
        "ts_utc": _now(),
        "engine_status": engine.get("status"),
        "engine_action": engine.get("action"),
        "dry_run": engine.get("dry_run"),
        "intent_check_rc": rc,
        "intent_check_result": (intent or {}).get("result"),
        "watchdog_tail": tail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-input-json", type=Path, default=DEFAULT_ENGINE)
    ap.add_argument("--watchdog-log-jsonl", type=Path, default=DEFAULT_WATCHDOG)
    ap.add_argument("--checkpoint-minutes", type=str, default="5,15,30")
    ap.add_argument("--no-wait", action="store_true", help="Take checkpoints immediately (smoke mode).")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    mins = [int(x.strip()) for x in str(args.checkpoint_minutes).split(",") if x.strip()]
    mins = sorted(set(m for m in mins if m >= 0))
    if not mins:
        mins = [5, 15, 30]

    start_ts = time.time()
    started_utc = _now()
    snapshots: list[dict[str, Any]] = []

    # T+0 snapshot
    snapshots.append(_checkpoint_snapshot("T+0", args.engine_input_json, args.watchdog_log_jsonl))

    for m in mins:
        if args.no_wait:
            snapshots.append(_checkpoint_snapshot(f"T+{m}m", args.engine_input_json, args.watchdog_log_jsonl))
            continue
        target = start_ts + (m * 60)
        while time.time() < target:
            time.sleep(1)
        snapshots.append(_checkpoint_snapshot(f"T+{m}m", args.engine_input_json, args.watchdog_log_jsonl))

    final = snapshots[-1] if snapshots else {}
    fail_conditions = []
    if str(final.get("engine_status") or "") != "READY_FOR_ENGINE_SUBMIT":
        fail_conditions.append("engine_status_not_ready")
    if str(final.get("intent_check_result") or "") != "PASS":
        fail_conditions.append("intent_contract_fail")

    result = "PASS" if not fail_conditions else "FAIL"
    out = {
        "schema": "role_router_first30m_observer_v1",
        "generated_at_utc": _now(),
        "started_at_utc": started_utc,
        "checkpoints": snapshots,
        "result": result,
        "fail_conditions": fail_conditions,
        "note": "Operational observer for first-run submission monitoring.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"result={result}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
