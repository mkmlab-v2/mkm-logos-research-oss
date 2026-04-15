# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.6, M:0.4}
# Balance: 90
# Purpose: Monitor mode-router v3 canary health and append ops log.
# Keywords: canary, monitor, ops, rollback, swap_typo
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_DECISION = ART / "l1_inverse_decoder_mode_router_v3_canary_decision_v1.json"
DEFAULT_DAILY_GATE = ART / "l1_inverse_decoder_daily_gate_v1_latest.json"
DEFAULT_LONGSAMPLE_GATE = ART / "l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json"
DEFAULT_STATUS = ART / "l1_inverse_decoder_mode_router_v3_canary_status_latest.json"
DEFAULT_LOG = REPORTS / "l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-artifact", type=Path, default=DEFAULT_DECISION)
    ap.add_argument("--daily-gate-artifact", type=Path, default=DEFAULT_DAILY_GATE)
    ap.add_argument("--longsample-gate-artifact", type=Path, default=DEFAULT_LONGSAMPLE_GATE)
    ap.add_argument("--status-out", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--log-out", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--traffic-pct", type=int, default=10)
    ap.add_argument("--phase", type=str, default="phase_1")
    args = ap.parse_args()

    decision_doc = _read_json(args.decision_artifact if args.decision_artifact.is_absolute() else ROOT / args.decision_artifact)
    daily_doc = _read_json(args.daily_gate_artifact if args.daily_gate_artifact.is_absolute() else ROOT / args.daily_gate_artifact)
    long_doc = _read_json(
        args.longsample_gate_artifact if args.longsample_gate_artifact.is_absolute() else ROOT / args.longsample_gate_artifact
    )

    decision_ok = decision_doc.get("decision") == "GO_CANARY_MODE_ROUTER_V3_10PCT"
    daily_ok = bool(daily_doc.get("gate", {}).get("all_ok", False))
    long_ok = bool(long_doc.get("gate", {}).get("all_ok", False))

    canary_ok = decision_ok and daily_ok and long_ok
    action = "KEEP_CANARY" if canary_ok else "ROLLBACK_TO_V4"
    rollback_switch = decision_doc.get("rollback_policy", {}).get(
        "instant_disable_switch", "L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1"
    )

    status_doc = {
        "schema": "l1_inverse_decoder_mode_router_v3_canary_status_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "phase": args.phase,
        "traffic_pct": args.traffic_pct,
        "inputs": {
            "decision_artifact": str(args.decision_artifact),
            "daily_gate_artifact": str(args.daily_gate_artifact),
            "longsample_gate_artifact": str(args.longsample_gate_artifact),
        },
        "checks": {
            "canary_decision_ok": decision_ok,
            "daily_gate_ok": daily_ok,
            "longsample_gate_ok": long_ok,
        },
        "decision": {
            "canary_ok": canary_ok,
            "action": action,
            "rollback_switch": rollback_switch,
        },
        "metrics": {
            "daily_gate_decision": daily_doc.get("gate", {}).get("decision"),
            "longsample_gate_decision": long_doc.get("gate", {}).get("decision"),
            "swap_typo_delta_exact": long_doc.get("delta_vs_baseline", {}).get("swap_typo_exact_delta"),
            "swap_typo_delta_recovery": long_doc.get("delta_vs_baseline", {}).get("swap_typo_recovery_delta"),
            "swap_typo_p95_latency_delta_ms": long_doc.get("delta_vs_baseline", {}).get("swap_typo_p95_latency_delta_ms"),
        },
    }

    status_out = args.status_out if args.status_out.is_absolute() else ROOT / args.status_out
    log_out = args.log_out if args.log_out.is_absolute() else ROOT / args.log_out
    status_out.parent.mkdir(parents=True, exist_ok=True)
    log_out.parent.mkdir(parents=True, exist_ok=True)
    status_out.write_text(json.dumps(status_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_line = {
        "ts_utc": status_doc["generated_at_utc"],
        "schema": "l1_inverse_decoder_mode_router_v3_canary_log_v1",
        "phase": args.phase,
        "traffic_pct": args.traffic_pct,
        "action": action,
        "canary_ok": canary_ok,
        "daily_gate_decision": status_doc["metrics"]["daily_gate_decision"],
        "longsample_gate_decision": status_doc["metrics"]["longsample_gate_decision"],
        "swap_typo_delta_exact": status_doc["metrics"]["swap_typo_delta_exact"],
        "swap_typo_delta_recovery": status_doc["metrics"]["swap_typo_delta_recovery"],
        "swap_typo_p95_latency_delta_ms": status_doc["metrics"]["swap_typo_p95_latency_delta_ms"],
        "rollback_switch": rollback_switch,
    }
    with log_out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_line, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "status_out": str(status_out), "log_out": str(log_out), "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
