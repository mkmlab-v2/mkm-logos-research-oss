#!/usr/bin/env python3
"""
bridge_myeongni_alpha_pilot_v1

Micro-pilot bridge for Myeongni rail:
- Enforces manual promotion lock + track wall constraints
- Applies Myeongni as size-only multiplier (no direction override)
- Calls run_deriv_best_event_strike_v1.py for actual order routing
- Optionally runs meta-layer audit each loop
- Writes append-only pilot log JSONL
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


ROOT = _repo_root()
SCRIPTS = ROOT / "scripts"
TRADING_SCRIPTS = ROOT / "projects" / "bitcoin-trading" / "scripts"
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_PROMOTION_GATE = ART / "myeongni_promotion_gate_latest.json"
DEFAULT_MANUAL_LOCK = ART / "myeongni_manual_promotion_decision_lock_latest.json"
DEFAULT_LENS = ART / "myeongni_independent_lens_latest.json"
DEFAULT_COMMANDER_LENS = REPORTS / "commander_myeongni_lens_latest.json"
DEFAULT_LOG = REPORTS / "pilot_myeongni_trade_log_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _assert_gate_safety(gate_path: Path, lock_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    gate = _read_json(gate_path)
    lock = _read_json(lock_path)

    if str(gate.get("status") or "") != "PASS":
        raise SystemExit(f"promotion gate not PASS: {gate_path}")
    policy = gate.get("policy") if isinstance(gate.get("policy"), dict) else {}
    if bool(policy.get("track_b_to_a_auto_bridge")):
        raise SystemExit("track wall broken: track_b_to_a_auto_bridge must be false")
    if bool(policy.get("live_trigger_auto_enabled")):
        raise SystemExit("live trigger auto must stay disabled")
    if str(lock.get("final_decision") or "") != "approved":
        raise SystemExit(f"manual lock decision not approved: {lock_path}")
    return gate, lock


def _refresh_lens(lens_path: Path, use_recommended: bool) -> dict[str, Any]:
    cmd = [sys.executable, str(SCRIPTS / "run_lens_myeongni.py"), "--output", str(lens_path)]
    if use_recommended:
        cmd.append("--recommended")
    p = _run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"run_lens_myeongni failed: {p.stderr or p.stdout}")
    return _read_json(lens_path)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _effective_multiplier(base_multiplier: float, lens: dict[str, Any]) -> tuple[float, float]:
    scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    confidence = float(scores.get("confidence") or 0.5)
    confidence = _clamp(confidence, 0.1, 1.0)
    return base_multiplier * confidence, confidence


def _commander_multiplier(commander_lens: dict[str, Any]) -> tuple[float, float]:
    """
    Convert commander lens confidence to risk brake multiplier.
    Hard clamp: 0.1 ~ 1.0 (policy).
    """
    scores = commander_lens.get("scores") if isinstance(commander_lens.get("scores"), dict) else {}
    confidence = float(scores.get("confidence") or 0.5)
    return _clamp(confidence, 0.1, 1.0), confidence


def _round_qty(qty: float, precision: int = 6) -> float:
    return round(qty, precision)


def _audit_meta_layer(
    *,
    mission_id: str,
    actor: str,
    execution_allowed: bool,
    note: str,
) -> tuple[bool, str]:
    from mkm_meta_layer_envelope_v1 import AthenaValidator

    hold = "GO" if execution_allowed else "HOLD"
    violates = not bool(execution_allowed)
    envelope = {
        "schema": "mkm_meta_layer_turn_envelope_v1",
        "turn_id": f"myeongni-pilot-{int(time.time())}",
        "utc_timestamp": _utc_now(),
        "risk_tier": "MEDIUM",
        "premise_audit": {
            "question_bakes_in_answer": False,
            "hidden_premises": [],
            "fix_one_line": "Treat Myeongni as size-only overlay under manual lock.",
        },
        "objective_inversion": {
            "flip_sign_hypothesis": "Prioritize execution integrity over immediate fill.",
            "if_flipped_what_changes": "No forced order; retain bounded pilot loop.",
        },
        "stakeholder_remap": {
            "primary_auditor": "OPS_GATE",
            "success_criteria_for_auditor": "Gate lock and live flags remain constrained.",
            "failure_modes": [
                "track wall violated",
                "auto live trigger enabled",
                "schema validation failure",
            ],
        },
        "contradiction_check": {
            "violates_constitution_or_gates": violates,
            "hold_recommendation": hold,
            "evidence_paths": [
                str(DEFAULT_PROMOTION_GATE),
                str(DEFAULT_MANUAL_LOCK),
                "scripts/bridge_myeongni_alpha_pilot_v1.py",
            ],
        },
        "rival_hypotheses": {
            "H1": "Pilot can run safely with size-only bridge under manual lock.",
            "H2": "Audit or gate mismatch should block execution this turn.",
            "discriminating_observation": "Athena envelope validates and execution_allowed remains true.",
        },
        "minimal_experiment": {
            "smallest_test": "One-loop pilot run with bounded size and live flag.",
            "time_budget": "PT5M",
            "pass_signal": "Bridge exits 0 with compliant gate fields.",
            "fail_signal": "Audit block or non-zero script exit.",
        },
        "reentry_conditions": {
            "to_execution_requires": [
                "myeongni_promotion_gate status PASS",
                "manual decision lock approved",
                "meta-layer envelope validates",
            ],
            "blocked_until": [],
        },
        "self_refutation": {
            "what_would_falsify_my_plan": "Meta audit fails or order path violates track wall flags.",
            "strongest_counterargument": "A single-loop pilot may not provide statistical confidence.",
            "mitigation_or_accept": "Use this only as micro-pilot plumbing verification.",
        },
        "execution_barrier_labels": {
            "content_labels": ["[FACT]", "[RESEARCH_ONLY]"],
            "execution_allowed": bool(execution_allowed),
        },
    }
    validator = AthenaValidator(repo_root=ROOT)
    allowed, _norm, msg = validator.validate_and_audit(
        json.dumps(envelope, ensure_ascii=False),
        mission_id=mission_id,
        actor=actor,
        stage="meta_layer",
        append_log=True,
        evidence_path=str(DEFAULT_PROMOTION_GATE),
        note=note,
    )
    return bool(allowed), msg


def main() -> int:
    p = argparse.ArgumentParser(description="Run Myeongni size-only micro-pilot bridge.")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--qty", type=float, default=0.001, help="Base qty before Myeongni multiplier.")
    p.add_argument("--leverage", type=int, default=2)
    p.add_argument("--multiplier", type=float, default=0.05, help="Micro-pilot base size multiplier.")
    p.add_argument("--max-orders", type=int, default=1, help="Maximum successful order attempts.")
    p.add_argument("--interval-sec", type=int, default=300)
    p.add_argument(
        "--max-loops",
        type=int,
        default=0,
        help="Hard loop cap; 0 means unlimited until max-orders.",
    )
    p.add_argument("--min-qty", type=float, default=0.001)
    p.add_argument("--qty-precision", type=int, default=6)
    p.add_argument("--mainnet", action="store_true")
    p.add_argument("--live", action="store_true")
    p.add_argument("--allow-no-signal", action="store_true")
    p.add_argument("--meta-layer-audit", action="store_true")
    p.add_argument("--lens-recommended", action="store_true", help="Run lens in recommended mode.")
    p.add_argument("--use-commander-overlay", action="store_true", help="Apply commander risk brake multiplier.")
    p.add_argument("--commander-lens-json", type=Path, default=DEFAULT_COMMANDER_LENS)
    p.add_argument("--promotion-gate-json", type=Path, default=DEFAULT_PROMOTION_GATE)
    p.add_argument("--manual-lock-json", type=Path, default=DEFAULT_MANUAL_LOCK)
    p.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    p.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    p.add_argument("--mission-id", default="myeongni-micro-pilot")
    p.add_argument("--actor", default="bridge_myeongni_alpha_pilot_v1")
    args = p.parse_args()

    if args.qty <= 0.0:
        raise SystemExit("--qty must be positive")
    if args.multiplier <= 0.0 or args.multiplier > 1.0:
        raise SystemExit("--multiplier must be in (0, 1]")
    if args.max_orders <= 0:
        raise SystemExit("--max-orders must be >= 1")
    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be positive")
    if args.max_loops < 0:
        raise SystemExit("--max-loops must be >= 0")
    if args.min_qty <= 0.0:
        raise SystemExit("--min-qty must be positive")

    gate, lock = _assert_gate_safety(args.promotion_gate_json, args.manual_lock_json)
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)

    successes = 0
    loops = 0
    while successes < args.max_orders:
        loops += 1
        lens = _refresh_lens(args.lens_json, use_recommended=args.lens_recommended)
        eff_mul, conf = _effective_multiplier(args.multiplier, lens)
        commander_mul = 1.0
        commander_conf_raw = None
        if args.use_commander_overlay:
            commander_lens = _read_json(args.commander_lens_json)
            commander_mul, commander_conf_raw = _commander_multiplier(commander_lens)
            eff_mul = eff_mul * commander_mul
        eff_qty = _round_qty(args.qty * eff_mul, args.qty_precision)
        if eff_qty < args.min_qty:
            eff_qty = args.min_qty

        audit_allowed = True
        audit_msg = "audit_skipped"
        if args.meta_layer_audit:
            audit_allowed, audit_msg = _audit_meta_layer(
                mission_id=args.mission_id,
                actor=args.actor,
                execution_allowed=True,
                note=f"loop={loops};base_multiplier={args.multiplier};confidence={conf}",
            )
        if not audit_allowed:
            row = {
                "schema": "pilot_myeongni_trade_log_v1",
                "ts_utc": _utc_now(),
                "loop": loops,
                "status": "blocked_by_meta_layer",
                "audit_msg": audit_msg,
            }
            with args.log_jsonl.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            break

        cmd = [
            sys.executable,
            str(TRADING_SCRIPTS / "run_deriv_best_event_strike_v1.py"),
            "--symbol",
            args.symbol,
            "--qty",
            str(eff_qty),
            "--leverage",
            str(args.leverage),
        ]
        if args.mainnet:
            cmd.append("--mainnet")
        if args.live:
            cmd.append("--live")
        if args.allow_no_signal:
            cmd.append("--allow-no-signal")

        proc = _run(cmd)
        payload: dict[str, Any] = {}
        if proc.returncode == 0 and proc.stdout:
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError:
                payload = {}
        decision_path = Path(str(payload.get("out_json") or "")) if payload.get("out_json") else None
        decision = _read_json(decision_path) if decision_path and decision_path.is_file() else {}

        order_attempted = bool(payload.get("order_attempted"))
        order_rc = decision.get("order_rc")
        success = bool(args.live and order_attempted and isinstance(order_rc, int) and order_rc == 0)
        if success:
            successes += 1

        row = {
            "schema": "pilot_myeongni_trade_log_v1",
            "ts_utc": _utc_now(),
            "loop": loops,
            "symbol": args.symbol,
            "base_qty": args.qty,
            "effective_qty": eff_qty,
            "leverage": args.leverage,
            "base_multiplier": args.multiplier,
            "confidence_used": conf,
            "commander_overlay_enabled": bool(args.use_commander_overlay),
            "commander_lens_json": str(args.commander_lens_json) if args.use_commander_overlay else None,
            "commander_confidence_raw": commander_conf_raw,
            "size_multiplier_commander": commander_mul,
            "effective_multiplier": eff_mul,
            "min_qty_applied": eff_qty == args.min_qty,
            "live": bool(args.live),
            "mainnet": bool(args.mainnet),
            "signal": bool(payload.get("signal")),
            "order_attempted": order_attempted,
            "order_rc": order_rc,
            "order_success_assumed": success,
            "success_count_total": successes,
            "promotion_gate_status": gate.get("status"),
            "manual_lock_decision": lock.get("final_decision"),
            "track_b_to_a_auto_bridge": (gate.get("policy") or {}).get("track_b_to_a_auto_bridge"),
            "live_trigger_auto_enabled": (gate.get("policy") or {}).get("live_trigger_auto_enabled"),
            "meta_layer_audit_enabled": bool(args.meta_layer_audit),
            "meta_layer_audit_msg": audit_msg,
            "lens_json": str(args.lens_json),
            "decision_json": str(decision_path) if decision_path else None,
            "stdout_snippet": (proc.stdout or "")[:1500],
            "stderr_snippet": (proc.stderr or "")[:1500],
        }
        with args.log_jsonl.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

        if successes >= args.max_orders:
            break
        if args.max_loops > 0 and loops >= args.max_loops:
            break
        time.sleep(args.interval_sec)

    print(
        json.dumps(
            {
                "ok": True,
                "loops": loops,
                "successful_orders": successes,
                "max_orders": args.max_orders,
                "log_jsonl": str(args.log_jsonl),
                "live": bool(args.live),
                "mainnet": bool(args.mainnet),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
