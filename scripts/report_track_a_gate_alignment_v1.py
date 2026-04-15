# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Report Track A policy-floor vs runtime-floor alignment and decisions.
# Keywords: track_a, gate, alignment, policy, floor
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
KPI_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
SWEEP_POLICY = ROOT / "docs" / "final" / "artifacts" / "track_a_domain_cap_sweep_v1.json"
SWEEP_ALIGNED = ROOT / "docs" / "final" / "artifacts" / "track_a_domain_cap_sweep_aligned_v1.json"
SWEEP_RELAXED = ROOT / "docs" / "final" / "artifacts" / "track_a_domain_cap_sweep_relaxed_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_gate_alignment_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    active = _load(ACTIVE)
    kpi = _load(KPI_SUMMARY)
    sweep_policy = _load(SWEEP_POLICY)
    sweep_aligned = _load(SWEEP_ALIGNED)
    sweep_relaxed = _load(SWEEP_RELAXED)

    active_saving = float((active.get("compression_metrics") or {}).get("global_token_saving_rate", 0.0))
    policy_floor = float((kpi.get("active_kpi") or {}).get("ultra_saving_policy_min", 0.49))
    stale_kpi_saving = float((kpi.get("active_kpi") or {}).get("global_token_saving_rate", 0.0))
    runtime_drift = active_saving - stale_kpi_saving

    out_doc = {
        "schema": "track_a_gate_alignment_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "active_report": str(ACTIVE),
            "kpi_summary": str(KPI_SUMMARY),
            "sweep_policy_floor": str(SWEEP_POLICY),
            "sweep_aligned_floor": str(SWEEP_ALIGNED),
            "sweep_relaxed_floor": str(SWEEP_RELAXED),
        },
        "floors": {
            "policy_floor": policy_floor,
            "runtime_active_saving": active_saving,
            "stale_kpi_active_saving": stale_kpi_saving,
            "runtime_minus_stale_kpi": runtime_drift,
            "policy_floor_ok_now": active_saving >= policy_floor,
        },
        "sweep_decisions": {
            "policy_floor_049": {
                "decision": sweep_policy.get("decision"),
                "viable_count": int(sweep_policy.get("viable_count", 0)),
                "recommended": sweep_policy.get("recommended"),
            },
            "aligned_floor_runtime": {
                "decision": sweep_aligned.get("decision"),
                "viable_count": int(sweep_aligned.get("viable_count", 0)),
                "recommended": sweep_aligned.get("recommended"),
            },
            "relaxed_floor_046": {
                "decision": sweep_relaxed.get("decision"),
                "viable_count": int(sweep_relaxed.get("viable_count", 0)),
                "recommended": sweep_relaxed.get("recommended"),
            },
        },
        "conclusion": (
            "HOLD_BASELINE_TRACK_A_POLICY"
            if not (active_saving >= policy_floor)
            else "GO_POLICY_FLOOR_READY"
        ),
        "next_action": (
            "Keep Track A baseline under policy floor gate; use relaxed-floor result only as research evidence."
            if active_saving < policy_floor
            else "Proceed with policy-floor candidate promotion checks."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "conclusion": out_doc["conclusion"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
