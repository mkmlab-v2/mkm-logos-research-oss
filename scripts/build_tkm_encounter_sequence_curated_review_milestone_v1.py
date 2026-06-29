#!/usr/bin/env python3
"""Build TKM encounter_sequence curated human-review milestone rollup [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"

P44_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p44_gate_v1_latest.json"
CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_final_closure_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
REVIEW_MARK = ROOT / "reports/encounter_sequence_curated_review_mark_v1_latest.json"
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"

MILESTONE_REVIEWED_MIN = 6


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _registry_counts() -> dict[str, int]:
    pending = reviewed = total = 0
    if not REGISTRY.is_file():
        return {"pending_human_review": 0, "reviewed": 0, "total": 0}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        status = str(row.get("curated_path_status") or "")
        if status == "pending_human_review":
            pending += 1
        elif status in ("ingested_to_curated", "reviewed", "human_reviewed"):
            reviewed += 1
    return {"pending_human_review": pending, "reviewed": reviewed, "total": total}


def build() -> dict[str, Any]:
    p44 = _load(P44_GATE)
    closure = _load(CLOSURE)
    ack = _load(ACK)
    review = _load(REVIEW_MARK)
    review_counts = review.get("review_counts") if isinstance(review.get("review_counts"), dict) else {}
    if not review_counts:
        review_counts = _registry_counts()
    else:
        review_counts = dict(review_counts)

    human_ack_ok = ack.get("human_gate_ack") is True and ack.get("dummy_autofill") is not True
    reviewed = int(review_counts.get("reviewed") or 0)
    milestone_threshold_met = reviewed >= MILESTONE_REVIEWED_MIN

    milestone_ok = (
        p44.get("gate_ok") is True
        and closure.get("final_closure_ok") is True
        and human_ack_ok
        and (review.get("ok") is True or reviewed >= 1)
        and milestone_threshold_met
        and closure.get("research_only") is True
    )

    return {
        "schema": "tkm_encounter_sequence_curated_review_milestone_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "milestone_ok": milestone_ok,
        "milestone_reviewed_min": MILESTONE_REVIEWED_MIN,
        "milestone_threshold_met": milestone_threshold_met,
        "human_gate_ack_ok": human_ack_ok,
        "p44_gate_ok": p44.get("gate_ok"),
        "stack_final_closure_ok": closure.get("final_closure_ok"),
        "curated_review_mark_ok": review.get("ok"),
        "curated_review_marked_count": review.get("marked_count"),
        "curated_review_counts": review_counts,
        "interpret_gpu_train_attempted": closure.get("interpret_gpu_train_attempted"),
        "auto_training_forbidden": True,
        "note_ko": "P45 curated human-review milestone [HYPO][NON_GATING]; human-gate only; auto-training·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_curated_review_milestone_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--mirror-artifact", action="store_true", default=True)
    ap.add_argument("--no-mirror-artifact", action="store_false", dest="mirror_artifact")
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mirror_artifact:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out, ARTIFACT)
    counts = doc.get("curated_review_counts") if isinstance(doc.get("curated_review_counts"), dict) else {}
    print(
        json.dumps(
            {
                "ok": doc.get("milestone_ok"),
                "reviewed": counts.get("reviewed"),
                "milestone_min": doc.get("milestone_reviewed_min"),
            }
        )
    )
    return 0 if doc.get("milestone_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
