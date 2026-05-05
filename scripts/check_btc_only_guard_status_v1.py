#!/usr/bin/env python3
"""Thin health check for BTC-only guard status.

Reads:
- docs/final/artifacts/btrack_hypothesis_prophecy_latest.json

Writes:
- docs/final/artifacts/btc_only_guard_status_latest.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btc_only_guard_status_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-exit", action="store_true", help="Exit 2 when guard blocked=true.")
    ap.add_argument("--webhook-env", default="OPS_ALARM_WEBHOOK_URL")
    args = ap.parse_args(argv)

    if not args.hypothesis_json.is_file():
        print(f"ERROR: missing hypothesis json: {args.hypothesis_json}", file=sys.stderr)
        return 1
    doc = _load(args.hypothesis_json)
    pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
    meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    guard = meta.get("btc_only_guard") if isinstance(meta.get("btc_only_guard"), dict) else {}

    blocked = bool(guard.get("blocked"))
    instrument = str(pred.get("instrument") or "")
    direction = str(pred.get("direction") or "")
    violations = guard.get("violations") if isinstance(guard.get("violations"), list) else []
    status = "OK"
    if blocked:
        status = "BLOCKED"
    elif instrument != "btc":
        status = "INSTRUMENT_MISMATCH"

    out = {
        "schema": "btc_only_guard_status_v1",
        "ts_utc": _utc_now(),
        "status": status,
        "blocked": blocked,
        "instrument": instrument,
        "direction": direction,
        "violations": violations,
        "source_path": str(args.hypothesis_json.resolve()),
        "dispatch": {"status": "skipped", "reason": "not_applicable"},
    }
    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    should_dispatch = status in {"BLOCKED", "INSTRUMENT_MISMATCH"}
    if should_dispatch and webhook:
        payload = {
            "source": "btc_only_guard_status_v1",
            "status": status,
            "blocked": blocked,
            "instrument": instrument,
            "direction": direction,
            "violations": violations,
            "ts_utc": out["ts_utc"],
        }
        req = request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                out["dispatch"] = {"status": "sent", "http_status": int(resp.getcode())}
        except (error.URLError, TimeoutError) as exc:
            out["dispatch"] = {"status": "failed", "error": str(exc)}
    elif should_dispatch and not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")

    if args.strict_exit and blocked:
        return 2
    if status == "INSTRUMENT_MISMATCH":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
