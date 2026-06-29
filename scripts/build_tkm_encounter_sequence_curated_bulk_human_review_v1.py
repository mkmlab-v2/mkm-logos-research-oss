#!/usr/bin/env python3
"""Build TKM encounter_sequence curated bulk human-review rollup (post-P68) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"

P68_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p68_gate_v1_latest.json"
STACK_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json"
MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
REVIEW_MARK = ROOT / "reports/encounter_sequence_curated_review_mark_v1_latest.json"
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"

BULK_REVIEWED_MIN = 6


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
    p68 = _load(P68_GATE)
    stack = _load(STACK_CLOSURE)
    milestone = _load(MILESTONE)
    ack = _load(ACK)
    review = _load(REVIEW_MARK)
    counts = review.get("review_counts") if isinstance(review.get("review_counts"), dict) else {}
    if not counts:
        counts = _registry_counts()
    else:
        counts = dict(counts)

    human_ack_ok = ack.get("human_gate_ack") is True and ack.get("dummy_autofill") is not True
    reviewed = int(counts.get("reviewed") or 0)
    pending = int(counts.get("pending_human_review") or 0)
    total = int(counts.get("total") or 0)

    bulk_human_review_ok = (
        p68.get("gate_ok") is True
        and stack.get("ultra_grand_stack_stack_closure_ok") is True
        and stack.get("ultra_grand_stack_breakpoint_freeze") is True
        and milestone.get("milestone_ok") is True
        and human_ack_ok
        and reviewed >= BULK_REVIEWED_MIN
        and total >= reviewed
        and stack.get("research_only") is True
    )

    return {
        "schema": "tkm_encounter_sequence_curated_bulk_human_review_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "bulk_human_review_ok": bulk_human_review_ok,
        "p68_gate_ok": p68.get("gate_ok"),
        "ultra_grand_stack_breakpoint_freeze": stack.get("ultra_grand_stack_breakpoint_freeze"),
        "milestone_ok": milestone.get("milestone_ok"),
        "human_gate_ack_ok": human_ack_ok,
        "bulk_reviewed_min": BULK_REVIEWED_MIN,
        "curated_review_counts": counts,
        "curated_reviewed_count": reviewed,
        "curated_pending_human_review": pending,
        "curated_registry_total": total,
        "curated_review_mark_ok": review.get("ok"),
        "tier_inflation_forbidden": True,
        "auto_training_forbidden": True,
        "note_ko": "Post-P68 curated bulk human review [HYPO][NON_GATING]; human-gate only; P69+·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_curated_bulk_human_review_v1.py",
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
    print(
        json.dumps(
            {
                "ok": doc.get("bulk_human_review_ok"),
                "reviewed": doc.get("curated_reviewed_count"),
                "pending": doc.get("curated_pending_human_review"),
            }
        )
    )
    return 0 if doc.get("bulk_human_review_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
