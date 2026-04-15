# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-3 D1 routing condition A/B for Track A saving recovery.
# Keywords: track_a, routing, ab_test, saving_recovery, policy_floor
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_A = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
SPRINT_PLAN = ROOT / "docs" / "final" / "artifacts" / "track_a_saving_recovery_sprint_plan_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_routing_condition_ab_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_triplet(report: dict[str, Any]) -> tuple[float, float, float]:
    m = report.get("compression_metrics", {})
    return (
        float(m.get("global_token_saving_rate", 0.0)),
        float(m.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        float(m.get("avg_sensitive_integrity", 0.0)),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--sprint-plan", type=Path, default=SPRINT_PLAN)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.475)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    sprint_doc = _load_json(args.sprint_plan if args.sprint_plan.is_absolute() else ROOT / args.sprint_plan)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    gc = float(active_profile.get("general_max_saving_rate", 0.54))
    sc = float(active_profile.get("sensitive_max_saving_rate", 0.50))
    hc = float(active_profile.get("hangul_max_saving_rate", 0.48))

    common = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    arm_a = evaluate_report(input_doc, use_domain_router=True, **common)
    arm_b = evaluate_report(input_doc, use_domain_router=False, **common)
    a_save, a_jac, a_int = _metric_triplet(arm_a)
    b_save, b_jac, b_int = _metric_triplet(arm_b)

    candidate = (
        {
            "name": "arm_b_router_off",
            "saving": b_save,
            "jaccard": b_jac,
            "integrity": b_int,
            "delta_vs_arm_a": {
                "saving": b_save - a_save,
                "jaccard": b_jac - a_jac,
                "integrity": b_int - a_int,
            },
        }
        if b_save > a_save
        else {
            "name": "arm_a_router_on",
            "saving": a_save,
            "jaccard": a_jac,
            "integrity": a_int,
            "delta_vs_arm_a": {"saving": 0.0, "jaccard": 0.0, "integrity": 0.0},
        }
    )
    gate = {
        "saving_floor_ok": candidate["saving"] >= args.saving_floor,
        "integrity_floor_ok": candidate["integrity"] >= args.integrity_floor,
    }
    decision = (
        "GO_W3_D2_CAP_DECOUPLING"
        if gate["saving_floor_ok"] and gate["integrity_floor_ok"]
        else "HOLD_W3_D1_AND_KEEP_BASELINE"
    )

    out_doc = {
        "schema": "track_a_routing_condition_ab_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "sprint_plan": str(args.sprint_plan),
            "base_caps": {"general": gc, "sensitive": sc, "hangul": hc},
            "base_must_keep": sorted(BASE_MUST_KEEP),
        },
        "sprint_context": {
            "name": (sprint_doc.get("sprint") or {}).get("name"),
            "objective": (sprint_doc.get("sprint") or {}).get("objective"),
            "target_gate": "saving >= 0.475 and integrity == 1.0",
        },
        "arms": {
            "arm_a_router_on": {
                "saving": a_save,
                "jaccard": a_jac,
                "integrity": a_int,
            },
            "arm_b_router_off": {
                "saving": b_save,
                "jaccard": b_jac,
                "integrity": b_int,
                "delta_vs_arm_a": {
                    "saving": b_save - a_save,
                    "jaccard": b_jac - a_jac,
                    "integrity": b_int - a_int,
                },
            },
        },
        "candidate": candidate,
        "gate": gate,
        "decision": decision,
        "next_action": (
            "Proceed to W3-D2 cap decoupling sweep with the selected routing condition."
            if decision == "GO_W3_D2_CAP_DECOUPLING"
            else "Keep baseline routing and move to conservative cap/rule experiment for D2."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision, "candidate": candidate["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
