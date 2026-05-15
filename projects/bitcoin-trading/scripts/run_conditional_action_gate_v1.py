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
  7 — human execution approval validation failed (--human-approval-json or env)
  8 — frame payload validation failed (--frame-payload-json or env)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

SCHEMA_GATE = "conditional_action_gate_v1"
VALIDATOR_REL = Path("scripts/validate_trading_human_execution_approval_v1.py")
FRAME_VALIDATOR_REL = Path("scripts/validate_btc_frame_governance_payload_v1.py")


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


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def evaluate_tactical_long_override(
    doc: dict[str, Any],
    *,
    backend: str,
    side: Optional[str],
    qty: Optional[float],
    max_qty: float,
    min_breadth_ratio: float,
    min_net_buy_krw_eok: float,
    min_theme_score: float,
) -> Tuple[bool, str, dict[str, Any]]:
    evidence: dict[str, Any] = {"eligible": False}
    if backend != "api":
        return False, "tactical_backend_not_api", evidence
    if side != "BUY":
        return False, "tactical_side_not_buy", evidence
    if qty is None:
        return False, "tactical_qty_missing", evidence
    if qty > max_qty:
        evidence["qty"] = qty
        evidence["max_qty"] = max_qty
        return False, "tactical_qty_exceeds_cap", evidence

    pulse = doc.get("market_pulse")
    if not isinstance(pulse, dict):
        return False, "tactical_market_pulse_missing", evidence

    breadth_ratio = _to_float(pulse.get("advance_decline_ratio"))
    foreign_buy = _to_float(pulse.get("foreign_net_buy_krw_eok"))
    institution_buy = _to_float(pulse.get("institution_net_buy_krw_eok"))
    theme_score = _to_float(pulse.get("theme_leadership_score"))
    if None in (breadth_ratio, foreign_buy, institution_buy, theme_score):
        return False, "tactical_market_pulse_incomplete", evidence

    net_buy_sum = float(foreign_buy) + float(institution_buy)
    evidence.update(
        {
            "advance_decline_ratio": float(breadth_ratio),
            "net_buy_krw_eok_sum": net_buy_sum,
            "theme_leadership_score": float(theme_score),
        }
    )

    if float(breadth_ratio) < min_breadth_ratio:
        return False, "tactical_breadth_below_threshold", evidence
    if net_buy_sum < min_net_buy_krw_eok:
        return False, "tactical_net_buy_below_threshold", evidence
    if float(theme_score) < min_theme_score:
        return False, "tactical_theme_score_below_threshold", evidence

    evidence["eligible"] = True
    evidence["qty"] = qty
    evidence["max_qty"] = max_qty
    return True, "go_tactical_long_override", evidence


def _resolve_human_approval_path(
    root: Path,
    cli: Optional[Path],
    *,
    skip: bool,
) -> Optional[Path]:
    if skip:
        return None
    if cli is not None:
        p = cli if cli.is_absolute() else (root / cli)
        return p.resolve()
    env = os.environ.get("MKM_TRADING_HUMAN_APPROVAL_JSON", "").strip()
    if not env:
        return None
    ep = Path(env)
    return ep.resolve() if ep.is_absolute() else (root / ep).resolve()


def _run_human_approval_validator(root: Path, approval_path: Path) -> int:
    val = root / VALIDATOR_REL
    if not val.is_file():
        print(f"Missing human approval validator: {val}", file=sys.stderr)
        return 2
    proc = subprocess.run(
        [sys.executable, str(val), "--approval", str(approval_path)],
        cwd=str(root),
    )
    return int(proc.returncode) if proc.returncode is not None else 1


def _resolve_frame_payload_path(root: Path, cli: Optional[Path], *, skip: bool) -> Optional[Path]:
    if skip:
        return None
    if cli is not None:
        p = cli if cli.is_absolute() else (root / cli)
        return p.resolve()
    env = os.environ.get("MKM_BTC_FRAME_PAYLOAD_JSON", "").strip()
    if not env:
        return None
    ep = Path(env)
    return ep.resolve() if ep.is_absolute() else (root / ep).resolve()


def _run_frame_payload_validator(
    root: Path,
    payload_path: Path,
    *,
    risk_json: Path,
    approval_path: Optional[Path],
    require_live_eligible: bool,
) -> int:
    val = root / FRAME_VALIDATOR_REL
    if not val.is_file():
        print(f"Missing frame payload validator: {val}", file=sys.stderr)
        return 2
    cmd = [
        sys.executable,
        str(val),
        "--payload",
        str(payload_path),
        "--risk-json",
        str(risk_json.resolve()),
    ]
    if approval_path is not None:
        cmd.extend(["--approval-json", str(approval_path)])
    if require_live_eligible:
        cmd.append("--require-live-eligible")
    proc = subprocess.run(cmd, cwd=str(root))
    return int(proc.returncode) if proc.returncode is not None else 1


def _write_gate_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    ap.add_argument(
        "--dry-run-exit-zero-on-block",
        action="store_true",
        help="With --dry-run only: still write gate summary but exit 0 when gate blocks (scheduled Fact-Safe hygiene).",
    )
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
    ap.add_argument(
        "--human-approval-json",
        type=Path,
        default=None,
        help="Optional trading_human_execution_approval_v1 JSON; runs repo validator before backend.",
    )
    ap.add_argument(
        "--skip-human-approval",
        action="store_true",
        help="Ignore MKM_TRADING_HUMAN_APPROVAL_JSON and --human-approval-json.",
    )
    ap.add_argument(
        "--frame-payload-json",
        type=Path,
        default=None,
        help="Optional btc_frame_governance_stage_payload_v1 JSON; validates track/stage/risk/live contract.",
    )
    ap.add_argument(
        "--skip-frame-payload",
        action="store_true",
        help="Ignore --frame-payload-json and MKM_BTC_FRAME_PAYLOAD_JSON.",
    )
    ap.add_argument(
        "--enable-tactical-long",
        action="store_true",
        help="Allow limited BUY override in blocked state when market_pulse thresholds pass.",
    )
    ap.add_argument(
        "--tactical-max-qty",
        type=float,
        default=0.002,
        help="Maximum qty allowed for tactical long override.",
    )
    ap.add_argument(
        "--tactical-min-breadth-ratio",
        type=float,
        default=1.05,
        help="Minimum market breadth (advance/decline ratio).",
    )
    ap.add_argument(
        "--tactical-min-net-buy-krw-eok",
        type=float,
        default=30000.0,
        help="Minimum combined foreign+institution net buy (KRW eok).",
    )
    ap.add_argument(
        "--tactical-min-theme-score",
        type=float,
        default=0.70,
        help="Minimum theme leadership score in market_pulse.",
    )

    args = ap.parse_args(argv)

    if bool(args.dry_run_exit_zero_on_block) and not bool(args.dry_run):
        print("--dry-run-exit-zero-on-block requires --dry-run", file=sys.stderr)
        return 2

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

    if not ok and bool(args.enable_tactical_long):
        tactical_ok, tactical_reason, tactical_evidence = evaluate_tactical_long_override(
            doc,
            backend=args.backend,
            side=args.side,
            qty=args.qty,
            max_qty=float(args.tactical_max_qty),
            min_breadth_ratio=float(args.tactical_min_breadth_ratio),
            min_net_buy_krw_eok=float(args.tactical_min_net_buy_krw_eok),
            min_theme_score=float(args.tactical_min_theme_score),
        )
        summary["tactical_long"] = {
            "enabled": True,
            "ok": tactical_ok,
            "reason": tactical_reason,
            "evidence": tactical_evidence,
        }
        if tactical_ok:
            ok = True
            reason = tactical_reason
            summary["gate_ok"] = True
            summary["gate_reason"] = tactical_reason
            summary["gate_override"] = "tactical_long"
    else:
        summary["tactical_long"] = {"enabled": bool(args.enable_tactical_long)}

    _write_gate_summary(args.gate_summary, summary)

    if not ok:
        print(f"[gate:block] {reason} summary={args.gate_summary}", file=sys.stderr)
        if bool(args.dry_run) and bool(args.dry_run_exit_zero_on_block):
            return 0
        return 3

    print(f"[gate:pass] {reason} summary={args.gate_summary}")

    hap = _resolve_human_approval_path(
        root,
        args.human_approval_json,
        skip=bool(args.skip_human_approval),
    )
    if hap is not None:
        if not hap.is_file():
            print(f"Human approval file missing: {hap}", file=sys.stderr)
            return 2
        vrc = _run_human_approval_validator(root, hap)
        summary["human_approval_path"] = str(hap)
        summary["human_approval_validator_exit_code"] = vrc
        summary["human_approval_ok"] = vrc == 0
        _write_gate_summary(args.gate_summary, summary)
        if vrc != 0:
            print(
                f"[gate:human-approval-fail] validator_exit={vrc} summary={args.gate_summary}",
                file=sys.stderr,
            )
            return 7

    frame_payload = _resolve_frame_payload_path(
        root,
        args.frame_payload_json,
        skip=bool(args.skip_frame_payload),
    )
    if frame_payload is not None:
        if not frame_payload.is_file():
            print(f"Frame payload file missing: {frame_payload}", file=sys.stderr)
            return 2
        frame_rc = _run_frame_payload_validator(
            root,
            frame_payload,
            risk_json=risk_path,
            approval_path=hap,
            require_live_eligible=bool(args.backend == "api" and args.pass_live),
        )
        summary["frame_payload_path"] = str(frame_payload)
        summary["frame_payload_validator_exit_code"] = frame_rc
        summary["frame_payload_ok"] = frame_rc == 0
        _write_gate_summary(args.gate_summary, summary)
        if frame_rc != 0:
            print(
                f"[gate:frame-payload-fail] validator_exit={frame_rc} summary={args.gate_summary}",
                file=sys.stderr,
            )
            return 8

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
