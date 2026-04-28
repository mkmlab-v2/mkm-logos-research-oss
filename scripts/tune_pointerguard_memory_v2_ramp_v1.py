#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"

DECISION_DEFAULT = ART / "pointerguard_apply_go_promotion_decision_memory_latest.json"
POLICY_DEFAULT = ART / "pointerguard_folder_policy_latest.json"
OUT_DEFAULT = ART / "pointerguard_memory_v2_ramp_tuning_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-json", type=Path, default=DECISION_DEFAULT)
    ap.add_argument("--folder-policy-json", type=Path, default=POLICY_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    decision_path = args.decision_json if args.decision_json.is_absolute() else ROOT / args.decision_json
    policy_path = args.folder_policy_json if args.folder_policy_json.is_absolute() else ROOT / args.folder_policy_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    dec = _read_json(decision_path)
    policy = _read_json(policy_path)

    profile_id = str(dec.get("inputs", {}).get("profile_id", ""))
    profiles = policy.get("promotion_profiles", [])
    profile = {}
    for p in profiles if isinstance(profiles, list) else []:
        if isinstance(p, dict) and str(p.get("profile_id")) == profile_id:
            profile = p
            break

    thresholds = [float(x) for x in profile.get("ramp_unresolved_thresholds", [])] if profile else []
    current_index = int(profile.get("ramp_current_index", 0)) if profile else 0
    if thresholds:
        current_index = min(max(0, current_index), len(thresholds) - 1)

    checks = dec.get("recent_checks", [])
    pass_all = True
    if not checks:
        pass_all = False
    else:
        for c in checks:
            if not isinstance(c, dict):
                pass_all = False
                break
            if not bool(c.get("pass_apply_ratio", False)) or not bool(c.get("pass_apply_unresolved", False)):
                pass_all = False
                break

    recommended_index = current_index
    recommendation = "HOLD_INDEX"
    if pass_all and thresholds and current_index < len(thresholds) - 1:
        recommended_index = current_index + 1
        recommendation = "ADVANCE_TO_NEXT_TIGHTER_THRESHOLD"
    elif pass_all and thresholds and current_index == len(thresholds) - 1:
        recommendation = "RAMP_COMPLETE_READY_FOR_PROFILE_ENABLE_REVIEW"

    out_doc = {
        "schema": "pointerguard_memory_v2_ramp_tuning_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "decision_json": str(decision_path),
            "folder_policy_json": str(policy_path),
            "profile_id": profile_id,
        },
        "ramp": {
            "thresholds": thresholds,
            "current_index": current_index,
            "current_threshold": thresholds[current_index] if thresholds else None,
            "recommended_index": recommended_index,
            "recommended_threshold": thresholds[recommended_index] if thresholds else None,
        },
        "decision_checks": {
            "recent_check_count": len(checks) if isinstance(checks, list) else 0,
            "pass_all_recent_checks": pass_all,
            "original_decision": dec.get("decision"),
            "original_reasons": dec.get("reasons", []),
        },
        "recommendation": recommendation,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "recommendation": recommendation,
                "recommended_index": recommended_index,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
