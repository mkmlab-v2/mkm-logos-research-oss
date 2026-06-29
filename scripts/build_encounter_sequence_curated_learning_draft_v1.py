#!/usr/bin/env python3
"""Draft curated-learning pointers for encounter_sequence disagreements [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ledger_mod():
    path = ROOT / "scripts" / "encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load encounter_sequence_ledger_v1")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(*, paths: list[Path] | None = None) -> dict[str, Any]:
    mod = _ledger_mod()
    if paths:
        records: list[dict[str, Any]] = []
        for path in paths:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    obj = json.loads(line)
                    errs = mod.validate_encounter_sequence_record(obj)
                    if errs:
                        raise ValueError(f"{path}: {'; '.join(errs)}")
                    records.append(obj)
    else:
        records = mod.iter_ledger_records(ROOT)

    drafts: list[dict[str, Any]] = []
    for row in records:
        closure = row.get("physician_closure") if isinstance(row.get("physician_closure"), dict) else {}
        agr = closure.get("agreement") if isinstance(closure.get("agreement"), dict) else {}
        code = str(agr.get("disagreement_code") or "none")
        match = agr.get("ai_physician_match")
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if not closure or (code == "none" and match is not False):
            continue
        summary = row.get("sequence_summary") if isinstance(row.get("sequence_summary"), dict) else {}
        drafts.append(
            {
                "sequence_id": seq_id,
                "ref_token": enc.get("ref_token"),
                "disagreement_code": code,
                "ai_physician_match": match,
                "final_ai_constitution": summary.get("final_ai_constitution"),
                "physician_label": (closure.get("physician_constitution") or {}).get("label"),
                "curated_path_status": "pending_human_review",
                "human_gate_required": True,
                "track_a_bridge_forbidden": True,
                "note_ko": "[HYPO] AI 오판 지점 → human-curated correction path; auto-training 금지",
            }
        )

    draft_ok = True
    return {
        "schema": "encounter_sequence_curated_learning_draft_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "draft_ok": draft_ok,
        "disagreement_draft_count": len(drafts),
        "drafts": drafts,
        "reproduce": "py scripts/build_encounter_sequence_curated_learning_draft_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, action="append", default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(paths=args.path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["draft_ok"], "disagreement_draft_count": doc["disagreement_draft_count"]}))
    return 0 if doc["draft_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
