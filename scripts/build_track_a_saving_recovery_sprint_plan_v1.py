# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Build Track A saving recovery sprint plan under fixed policy floor.
# Keywords: track_a, sprint, recovery, policy_floor, plan
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_decision_v1.json"
ALIGN = ROOT / "docs" / "final" / "artifacts" / "track_a_gate_alignment_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_saving_recovery_sprint_plan_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision", type=Path, default=DECISION)
    ap.add_argument("--alignment", type=Path, default=ALIGN)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    decision = _load(args.decision if args.decision.is_absolute() else ROOT / args.decision)
    align = _load(args.alignment if args.alignment.is_absolute() else ROOT / args.alignment)

    floors = align.get("floors", {})
    policy_floor = float(floors.get("policy_floor", 0.49))
    runtime_saving = float(floors.get("runtime_active_saving", 0.0))
    gap = policy_floor - runtime_saving

    out_doc = {
        "schema": "track_a_saving_recovery_sprint_plan_v1",
        "generated_at_utc": _now_utc(),
        "guardrail": {
            "policy_floor_locked": policy_floor,
            "runtime_saving_now": runtime_saving,
            "gap_to_recover": gap,
            "decision_ref": str(args.decision),
            "decision_id": decision.get("decision"),
        },
        "sprint": {
            "name": "track_a_saving_recovery_week3",
            "objective": "Recover global token saving to policy floor without degrading integrity or jaccard gate.",
            "work_items": [
                {
                    "id": "W3-D1",
                    "title": "Domain-routing condition split A/B",
                    "owner": "agent",
                    "deliverable": "track_a_routing_condition_ab_v1.json",
                    "success_gate": "saving >= 0.475 and integrity == 1.0",
                },
                {
                    "id": "W3-D2",
                    "title": "Cap decoupling by sensitive/hangul only",
                    "owner": "agent",
                    "deliverable": "track_a_cap_decouple_sweep_v1.json",
                    "success_gate": "saving >= 0.48 and target-domain jaccard non-regression",
                },
                {
                    "id": "W3-D3",
                    "title": "Conservative phrase-first profile test",
                    "owner": "agent",
                    "deliverable": "track_a_phrase_profile_ab_v1.json",
                    "success_gate": "saving >= 0.485 and integrity == 1.0",
                },
                {
                    "id": "W3-D4",
                    "title": "Final candidate replay under policy floor",
                    "owner": "agent",
                    "deliverable": "track_a_policy_floor_replay_v1.json",
                    "success_gate": f"saving >= {policy_floor} and integrity == 1.0",
                },
            ],
            "stop_conditions": [
                "Any integrity drop below 1.0",
                "Any policy-floor claim without artifact proof",
                "Any attempt to downgrade policy floor in runtime-only scripts",
            ],
        },
        "next_action": "Start W3-D1 and keep commercialization status at HOLD until replay gate passes.",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "gap_to_recover": gap}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
