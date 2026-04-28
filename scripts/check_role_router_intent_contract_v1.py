#!/usr/bin/env python3
"""Verify SSH trading payload follows local-master intent contract."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ENGINE_INPUT = ART / "btc_limited_live_engine_input_from_role_router_latest.json"
DEFAULT_OUT = ART / "role_router_intent_contract_check_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-input-json", type=Path, default=DEFAULT_ENGINE_INPUT)
    ap.add_argument("--expected-symbol", type=str, default="BTCUSDT")
    ap.add_argument("--expected-size-usd", type=float, default=10.0)
    ap.add_argument("--expected-max-losses", type=int, default=3)
    ap.add_argument("--expected-max-dd-pct", type=float, default=2.0)
    ap.add_argument("--expected-router-type", type=str, default="role_mapping_optimized")
    ap.add_argument("--expected-coord-policy", type=str, default="off")
    ap.add_argument("--expected-min-n-days", type=int, default=20)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _read(args.engine_input_json)
    guards = doc.get("guards") or {}
    engine_input = doc.get("engine_input") or {}
    params = engine_input.get("candidate_params") or {}
    metrics = engine_input.get("candidate_metrics") or {}

    checks = {
        "status_ready_for_submit": str(doc.get("status") or "") == "READY_FOR_ENGINE_SUBMIT",
        "action_submit_to_queue": str(doc.get("action") or "") == "submit_to_engine_queue",
        "symbol_match": str(doc.get("symbol") or "") == str(args.expected_symbol),
        "dry_run_true": bool(doc.get("dry_run")),
        "candidate_tradable_true": bool(guards.get("candidate_tradable")),
        "signoff_approve_true": bool(guards.get("signoff_approve")),
        "signoff_mode_limited_live_true": bool(guards.get("signoff_mode_limited_live")),
        "approve_submit_flag_true": bool(guards.get("approve_submit_flag")),
        "size_usd_match": float(engine_input.get("size_usd") or 0.0) == float(args.expected_size_usd),
        "max_losses_match": int(engine_input.get("max_consecutive_losses") or -1) == int(args.expected_max_losses),
        "max_dd_match": float(engine_input.get("max_drawdown_pct") or 0.0) == float(args.expected_max_dd_pct),
        "auto_scale_up_false": bool(engine_input.get("auto_scale_up")) is False,
        "auto_bridge_disabled": bool(engine_input.get("auto_bridge_enabled")) is False,
        "auto_live_trigger_disabled": bool(engine_input.get("auto_live_trigger_enabled")) is False,
        "router_type_match": str(params.get("router_type") or "") == str(args.expected_router_type),
        "coord_policy_match": str(params.get("coord_policy") or "") == str(args.expected_coord_policy),
        "min_n_days_guard": int(metrics.get("n_days") or 0) >= int(args.expected_min_n_days),
    }

    failed = [k for k, v in checks.items() if not bool(v)]
    result = "PASS" if not failed else "FAIL"

    payload = {
        "schema": "role_router_intent_contract_check_v1",
        "generated_at_utc": _now(),
        "engine_input_json": str(args.engine_input_json.resolve()),
        "result": result,
        "failed_checks": failed,
        "checks": checks,
        "snapshot": {
            "symbol": doc.get("symbol"),
            "status": doc.get("status"),
            "action": doc.get("action"),
            "candidate_params": params,
            "candidate_metrics": metrics,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"result={result}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
