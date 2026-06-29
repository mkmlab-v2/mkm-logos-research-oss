#!/usr/bin/env python3
"""Mark curated-learning registry rows human-reviewed (no auto-training) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
REGISTRY = ROOT / "data/clinic/encounter_sequence_curated_learning_registry_v1.jsonl"
OUT = ROOT / "reports/encounter_sequence_curated_review_mark_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry_rows() -> list[dict[str, Any]]:
    if not REGISTRY.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _review_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    pending = reviewed = total = 0
    for row in rows:
        total += 1
        status = str(row.get("curated_path_status") or "")
        if status == "pending_human_review":
            pending += 1
        elif status in ("ingested_to_curated", "reviewed", "human_reviewed"):
            reviewed += 1
    return {"pending_human_review": pending, "reviewed": reviewed, "total": total}


def run(*, max_mark: int = 6) -> dict[str, Any]:
    if not ACK.is_file():
        return {"ok": False, "reason": "human_gate_ack_missing"}
    ack = json.loads(ACK.read_text(encoding="utf-8-sig"))
    if ack.get("human_gate_ack") is not True or ack.get("dummy_autofill") is True:
        return {"ok": False, "reason": "human_gate_ack_required"}

    drafts_doc = json.loads(DRAFTS.read_text(encoding="utf-8-sig")) if DRAFTS.is_file() else {}
    drafts = drafts_doc.get("drafts") if isinstance(drafts_doc.get("drafts"), list) else []
    existing = _load_registry_rows()
    already_reviewed = {
        str(r.get("sequence_id"))
        for r in existing
        if str(r.get("curated_path_status") or "") in ("ingested_to_curated", "reviewed", "human_reviewed")
    }

    marked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for d in drafts:
        if not isinstance(d, dict):
            continue
        seq = str(d.get("sequence_id") or "")
        if not seq or seq in seen or seq in already_reviewed:
            continue
        seen.add(seq)
        row = {
            "schema": "encounter_sequence_curated_learning_registry_row_v1",
            "recorded_at_utc": _utc(),
            "sequence_id": seq,
            "disagreement_code": d.get("disagreement_code"),
            "curated_path_status": "ingested_to_curated",
            "human_gate_ack": True,
            "human_review_marked": True,
            "auto_training_forbidden": True,
            "note_ko": "human review mark [HYPO]; registry append-only; auto-training·Track A 금지.",
        }
        marked.append(row)
        if len(marked) >= max(1, max_mark):
            break

    if marked:
        REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRY.open("a", encoding="utf-8") as f:
            for row in marked:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    after = _review_counts(_load_registry_rows())
    ok = after.get("reviewed", 0) >= 1
    return {
        "schema": "encounter_sequence_curated_review_mark_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "ok": ok,
        "marked_count": len(marked),
        "review_counts": after,
        "auto_training_forbidden": True,
        "reproduce": "py scripts/run_encounter_sequence_curated_review_mark_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-mark", type=int, default=6)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(max_mark=args.max_mark)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "marked": doc.get("marked_count")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
