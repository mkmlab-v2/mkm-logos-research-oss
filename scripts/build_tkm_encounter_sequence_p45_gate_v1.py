#!/usr/bin/env python3
"""TKM encounter_sequence P45 gate: curated human-review milestone [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P44_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p44_gate_v1_latest.json"
MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p45_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p44 = _load(P44_GATE)
    milestone = _load(MILESTONE)
    weekly = _load(WEEKLY)
    cm = weekly.get("curated_review_milestone_kpi") if isinstance(weekly.get("curated_review_milestone_kpi"), dict) else {}
    counts = milestone.get("curated_review_counts") if isinstance(milestone.get("curated_review_counts"), dict) else {}

    checks = {
        "p44_gate_ok": {"passed": p44.get("gate_ok") is True},
        "milestone_ok": {"passed": milestone.get("milestone_ok") is True},
        "milestone_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "human_gate_ack_ok": {"passed": milestone.get("human_gate_ack_ok") is True},
        "milestone_threshold_met": {"passed": milestone.get("milestone_threshold_met") is True},
        "curated_reviewed_min": {
            "passed": int(counts.get("reviewed") or 0) >= int(milestone.get("milestone_reviewed_min") or 6),
        },
        "weekly_milestone_sync_ok": {"passed": cm.get("curated_review_milestone_headline_ok") is True},
        "auto_training_forbidden": {"passed": milestone.get("auto_training_forbidden") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p45_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p45_status": "curated_human_review_milestone_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "milestone_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p45_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p45_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
