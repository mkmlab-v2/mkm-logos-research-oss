# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.4}
# Balance: 90
# Purpose: Build canary decision artifact for mode-router v3 rollout.
# Keywords: canary, rollout, gate, swap_typo, mode-router-v3
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "l1_inverse_decoder_mode_router_v3_canary_decision_v1.json"
DEFAULT_DAILY_GATE = ART / "l1_inverse_decoder_daily_gate_v1_latest.json"
DEFAULT_CANDIDATE_GATE = ART / "l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-gate", type=Path, default=DEFAULT_DAILY_GATE)
    ap.add_argument("--candidate-gate", type=Path, default=DEFAULT_CANDIDATE_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    daily = _load_json(args.daily_gate if args.daily_gate.is_absolute() else ROOT / args.daily_gate)
    candidate = _load_json(args.candidate_gate if args.candidate_gate.is_absolute() else ROOT / args.candidate_gate)

    daily_ok = bool(daily.get("gate", {}).get("all_ok", False))
    candidate_ok = bool(candidate.get("gate", {}).get("all_ok", False))

    decision = "GO_CANARY_MODE_ROUTER_V3_10PCT" if (daily_ok and candidate_ok) else "HOLD_CANARY_KEEP_V4"
    rollout_plan = {
        "phase_1": {
            "traffic_pct": 10,
            "duration_hours": 24,
            "success_criteria": [
                "daily gate remains GO_KEEP_OBJECTIVE_V4_DEFAULT_ON",
                "no latency p95 regression > +2ms/sample vs baseline window",
                "no new alert for swap_typo floor breach",
            ],
        },
        "phase_2": {
            "traffic_pct": 30,
            "duration_hours": 48,
            "requires_phase_1_pass": True,
        },
        "phase_3": {
            "traffic_pct": 100,
            "duration_hours": 0,
            "requires_phase_2_pass": True,
        },
    }
    rollback = {
        "instant_disable_switch": "L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1",
        "fallback_command": "py scripts/run_l1_inverse_decoder_spike_test.py --disable-swap-typo-objective-v4",
        "trigger_any": [
            "daily gate decision != GO_KEEP_OBJECTIVE_V4_DEFAULT_ON",
            "candidate latency check false",
            "swap_typo exact/recovery floor breach on daily gate",
        ],
    }

    out_doc = {
        "schema": "l1_inverse_decoder_mode_router_v3_canary_decision_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "inputs": {
            "daily_gate_artifact": str(args.daily_gate),
            "candidate_gate_artifact": str(args.candidate_gate),
        },
        "upstream_checks": {
            "daily_gate_all_ok": daily_ok,
            "candidate_gate_all_ok": candidate_ok,
            "daily_gate_decision": daily.get("gate", {}).get("decision"),
            "candidate_gate_decision": candidate.get("gate", {}).get("decision"),
        },
        "decision": decision,
        "rollout_plan": rollout_plan,
        "rollback_policy": rollback,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
