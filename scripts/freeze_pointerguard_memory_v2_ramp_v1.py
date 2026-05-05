#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"

POLICY_DEFAULT = ART / "pointerguard_folder_policy_latest.json"
MEMORY_DECISION_DEFAULT = ART / "pointerguard_apply_go_promotion_decision_memory_latest.json"
OUT_DEFAULT = ART / "pointerguard_memory_v2_ramp_freeze_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folder-policy-json", type=Path, default=POLICY_DEFAULT)
    ap.add_argument("--memory-decision-json", type=Path, default=MEMORY_DECISION_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    policy_path = args.folder_policy_json if args.folder_policy_json.is_absolute() else ROOT / args.folder_policy_json
    decision_path = args.memory_decision_json if args.memory_decision_json.is_absolute() else ROOT / args.memory_decision_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    policy = _read_json(policy_path)
    decision = _read_json(decision_path)

    decision_ok = str(decision.get("decision", "")) == "PROMOTE_APPLY_GO"
    decision_reasons = decision.get("reasons", [])
    profile_id = str(decision.get("inputs", {}).get("profile_id", "memory_v2_apply"))

    frozen = False
    updated = False
    current_index: int | None = None
    max_index: int | None = None

    profiles = policy.get("promotion_profiles", [])
    if isinstance(profiles, list):
        for p in profiles:
            if not isinstance(p, dict) or str(p.get("profile_id", "")) != profile_id:
                continue
            thresholds = p.get("ramp_unresolved_thresholds", [])
            if isinstance(thresholds, list) and thresholds:
                max_index = len(thresholds) - 1
            current_index = int(p.get("ramp_current_index", 0))
            if decision_ok and not decision_reasons and max_index is not None and current_index >= max_index:
                if not bool(p.get("ramp_frozen", False)):
                    p["ramp_frozen"] = True
                    updated = True
                frozen = True
            else:
                frozen = bool(p.get("ramp_frozen", False))
            break

    if updated:
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_doc = {
        "schema": "pointerguard_memory_v2_ramp_freeze_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "folder_policy_json": str(policy_path),
            "memory_decision_json": str(decision_path),
            "profile_id": profile_id,
        },
        "updated": updated,
        "ramp_frozen": frozen,
        "ramp_current_index": current_index,
        "ramp_max_index": max_index,
        "memory_decision": decision.get("decision"),
        "memory_reasons": decision_reasons,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "updated": updated, "ramp_frozen": frozen}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
