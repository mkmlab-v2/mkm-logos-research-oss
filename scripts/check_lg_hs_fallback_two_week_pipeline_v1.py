#!/usr/bin/env python3
"""Validate lg_hs_fallback_two_week_pipeline_v1.json structure (local gate)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "docs/final/artifacts/lg_hs_fallback_two_week_pipeline_v1.json"
FOLLOWUP = ROOT / "docs/final/artifacts/lg_hs_meeting_followup_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    if not PIPELINE.is_file():
        raise SystemExit(f"missing: {PIPELINE}")

    doc = json.loads(PIPELINE.read_text(encoding="utf-8"))
    assert doc.get("schema") == "lg_hs_fallback_two_week_pipeline_v1"
    actions = doc.get("two_week_actions")
    if not isinstance(actions, list) or len(actions) < 5:
        raise SystemExit("two_week_actions must have at least 5 entries")
    candidates = doc.get("program_candidates")
    if not isinstance(candidates, list) or len(candidates) < 3:
        raise SystemExit("program_candidates must have at least 3 entries")

    triggered = False
    if FOLLOWUP.is_file():
        fu = json.loads(FOLLOWUP.read_text(encoding="utf-8"))
        oc = (fu.get("outcome_record_template") or {}).get("outcome_class")
        triggered = oc in ("hold", "reject")

    payload = {
        "ok": True,
        "pipeline": str(PIPELINE.relative_to(ROOT)).replace("\\", "/"),
        "action_count": len(actions),
        "candidate_count": len(candidates),
        "lg_fallback_triggered": triggered,
        "primary_lane_selected": doc.get("primary_lane_selected"),
    }
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
