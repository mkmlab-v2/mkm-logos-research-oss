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
TUNING_DEFAULT = ART / "pointerguard_memory_v2_ramp_tuning_latest.json"
OUT_DEFAULT = ART / "pointerguard_memory_v2_ramp_update_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folder-policy-json", type=Path, default=POLICY_DEFAULT)
    ap.add_argument("--tuning-json", type=Path, default=TUNING_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    policy_path = args.folder_policy_json if args.folder_policy_json.is_absolute() else ROOT / args.folder_policy_json
    tuning_path = args.tuning_json if args.tuning_json.is_absolute() else ROOT / args.tuning_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    policy = _read_json(policy_path)
    tuning = _read_json(tuning_path)
    recommendation = str(tuning.get("recommendation", "HOLD_INDEX"))
    profile_id = str(tuning.get("inputs", {}).get("profile_id", ""))
    recommended_index = tuning.get("ramp", {}).get("recommended_index")

    updated = False
    previous_index: int | None = None
    applied_index: int | None = None

    if recommendation == "ADVANCE_TO_NEXT_TIGHTER_THRESHOLD" and isinstance(recommended_index, int):
        profiles = policy.get("promotion_profiles", [])
        if isinstance(profiles, list):
            for p in profiles:
                if not isinstance(p, dict):
                    continue
                if str(p.get("profile_id", "")) != profile_id:
                    continue
                if bool(p.get("ramp_frozen", False)):
                    previous_index = int(p.get("ramp_current_index", 0))
                    updated = False
                    break
                previous_index = int(p.get("ramp_current_index", 0))
                p["ramp_current_index"] = int(recommended_index)
                applied_index = int(recommended_index)
                updated = True
                break

    if updated:
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_doc = {
        "schema": "pointerguard_memory_v2_ramp_update_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "folder_policy_json": str(policy_path),
            "tuning_json": str(tuning_path),
            "profile_id": profile_id,
            "recommendation": recommendation,
        },
        "updated": updated,
        "previous_index": previous_index,
        "applied_index": applied_index,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "updated": updated, "applied_index": applied_index}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
