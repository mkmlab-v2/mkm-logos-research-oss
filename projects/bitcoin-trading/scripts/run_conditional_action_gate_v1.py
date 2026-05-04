#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pluggable Fact-Safe gate: evaluates risk profile, then invokes one backend:

  --backend webhook → ``poc_binance_signal_webhook_spike_v1.py``
  --backend api     → ``execute_binance_usdm_single_order_v1.py``

Gate rules: same as legacy webhook gate (LOCKED / expiry / governance).

Exit codes:
  0 — gate passed and backend exited 0
  1 — gate passed but backend failed
  2 — invalid arguments / missing files
  3 — gate blocked
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

SCHEMA_GATE = "conditional_action_gate_v1"


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


DEFAULT_RISK_REL = Path("projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json")
POC_REL = Path("projects/bitcoin-trading/scripts/poc_binance_signal_webhook_spike_v1.py")
EXEC_REL = Path("projects/bitcoin-trading/scripts/execute_binance_usdm_single_order_v1.py")
SUMMARY_DEFAULT = Path("reports/poc_binance_signal_webhook/conditional_gate_latest.json")


def _parse_iso_utc(s: str) -> Optional[datetime]:
    raw = (s or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def evaluate_gate(
    doc: dict[str, Any],
    *,
    ignore_expiry: bool,
    allow_unknown: bool,
) -> Tuple[bool, str]:
    now = datetime.now(timezone.utc)

    if not ignore_expiry:
        exp_raw = doc.get("expires_at")
        if exp_raw is not None:
            exp_dt = _parse_iso_utc(str(exp_raw))
            if exp_dt is not None and now > exp_dt:
                return False, "risk_profile_expired"

    tg = doc.get("trinity_governor")
    if isinstance(tg, dict):
        mode = str(tg.get("mode") or "").strip().upper()
        if mode == "LOCKED_MODE":
            return False, "trinity_governor_LOCKED_MODE"
        if mode == "ACTIVE_MODE":
            gb = doc.get("governance_bridge")
            if isinstance(gb, dict) and gb.get("final_action_allowed") is False:
                return False, "governance_final_action_denied"
            return True, "go_trinity_ACTIVE_MODE"

    gb = doc.get("governance_bridge")
    if isinstance(gb, dict):
        if gb.get("final_action_allowed") is False:
            return False, "governance_final_action_denied"
        if gb.get("final_action_allowed") is True:
            return True, "go_governance_bridge_allow"

    notes = str(doc.get("notes") or "")
    if "LOCKED_MODE enforced" in notes:
        return False, "notes_LOCKED_MODE_enforced"
    if "ACTIVE_MODE" in notes and allow_unknown:
        return True, "go_notes_ACTIVE_heuristic"

    if allow_unknown:
        return True, "go_allow_unknown"

    return False, "gate_unknown_or_insufficient_signal"


def main(argv: list[str] | None = None) -> int:
    root = _workspace_root()
    ap = argparse.ArgumentParser(description="Fact-Safe gate → webhook PoC or single-shot API order.")
    ap.add_argument("--backend", choices=("webhook", "api"), required=True)
    ap.add_argument(
        "--risk-json",
        type=Path,
        default=root / DEFAULT_RISK_REL,
        help="Fact-Safe risk profile JSON.",
    )
    ap.add_argument("--ignore-expiry", action="store_true")
    ap.add_argument("--allow-unknown-gate", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Evaluate gate only; do not run backend.")
    ap.add_argument("--gate-summary", type=Path, default=SUMMARY_DEFAULT)

    # webhook backend
    ap.add_argument("--payload-file", type=Path, default=None)
    ap.add_argument("--poc-dry-run", action="store_true")
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--retries", type=int, default=None)
    ap.add_argument("--webhook-out", type=Path, default=None, dest="webhook_out")
    ap.add_argument("--url-env", default=None)
    ap.add_argument("--secret-env", default=None)

    # api backend
    ap.add_argument("--symbol", default=None)
    ap.add_argument("--side", choices=("BUY", "SELL"), default=None)
    ap.add_argument("--qty", type=float, default=None)
    ap.add_argument("--leverage", type=int, default=2)
    ap.add_argument("--mainnet", action="store_true", help="Passed to executor as mainnet mode.")
    ap.add_argument(
        "--pass-live",
        action="store_true",
        help="Forward --live to execute_binance_usdm_single_order (actually submit order).",
    )
    ap.add_argument("--executor-out", type=Path, default=None)

    args = ap.parse_args(argv)

    risk_path = args.risk_json
    if not risk_path.is_file():
        print(f"Missing risk profile: {risk_path}", file=sys.stderr)
        return 2

    try:
        doc = json.loads(risk_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Invalid risk JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(doc, dict):
        print("Risk profile must be a JSON object.", file=sys.stderr)
        return 2

    ok, reason = evaluate_gate(
        doc,
        ignore_expiry=bool(args.ignore_expiry),
        allow_unknown=bool(args.allow_unknown_gate),
    )

    summary: dict[str, Any] = {
        "schema": SCHEMA_GATE,
        "gate_ok": ok,
        "gate_reason": reason,
        "risk_json": str(risk_path.resolve()),
        "backend": args.backend,
    }

    args.gate_summary.parent.mkdir(parents=True, exist_ok=True)
    args.gate_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not ok:
        print(f"[gate:block] {reason} summary={args.gate_summary}", file=sys.stderr)
        return 3

    print(f"[gate:pass] {reason} summary={args.gate_summary}")

    if args.dry_run:
        print("[gate:dry-run] backend not invoked.")
        return 0

    if args.backend == "webhook":
        if not args.payload_file or not args.payload_file.is_file():
            print("--payload-file required for backend webhook (existing JSON path).", file=sys.stderr)
            return 2
        poc = root / POC_REL
        if not poc.is_file():
            print(f"Missing PoC script: {poc}", file=sys.stderr)
            return 2
        cmd: list[str] = [sys.executable, str(poc), "--payload-file", str(args.payload_file)]
        if args.poc_dry_run:
            cmd.append("--dry-run")
        if args.timeout is not None:
            cmd.extend(["--timeout", str(args.timeout)])
        if args.retries is not None:
            cmd.extend(["--retries", str(args.retries)])
        if args.webhook_out is not None:
            cmd.extend(["--out", str(args.webhook_out)])
        if args.url_env:
            cmd.extend(["--url-env", args.url_env])
        if args.secret_env:
            cmd.extend(["--secret-env", args.secret_env])
        proc = subprocess.run(cmd, cwd=str(root))
        return int(proc.returncode) if proc.returncode is not None else 1

    # api backend
    if not args.symbol or args.side is None or args.qty is None:
        print("--symbol, --side BUY|SELL, --qty required for backend api.", file=sys.stderr)
        return 2

    exe = root / EXEC_REL
    if not exe.is_file():
        print(f"Missing executor: {exe}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        str(exe),
        "--symbol",
        str(args.symbol),
        "--side",
        str(args.side),
        "--qty",
        str(args.qty),
        "--leverage",
        str(args.leverage),
    ]
    if args.mainnet:
        cmd.append("--mainnet")
    if args.pass_live:
        cmd.append("--live")
    if args.executor_out is not None:
        cmd.extend(["--out", str(args.executor_out)])

    proc = subprocess.run(cmd, cwd=str(root))
    return int(proc.returncode) if proc.returncode is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
