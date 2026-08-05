#!/usr/bin/env python3
"""Build conflict_surface JSON from a Logos reading pack slice (Job/Isaiah pattern).

Reproduce:
  py scripts/build_logos_studio_reading_pack_conflict_surface_v1.py \\
    --reading-pack docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json \\
    --conflict-group-id MKM_CONCEPT_JOB_SUFFERING \\
    --lexicon-base "Job suffering · reading pack 3-way" \\
    --out docs/final/artifacts/job_studio_conflict_surface_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _verse_refs(pack: dict[str, Any]) -> list[str]:
    refs = pack.get("verse_refs") or []
    out: list[str] = []
    for ref in refs:
        s = str(ref).strip()
        if s:
            out.append(s)
    return out[:12]


def build_from_reading_pack(
    doc: dict[str, Any],
    *,
    conflict_group_id: str,
    lexicon_base: str,
) -> dict[str, Any]:
    packs = doc.get("reading_packs") or []
    schools: list[dict[str, Any]] = []
    for idx, pack in enumerate(packs, start=1):
        if not isinstance(pack, dict):
            continue
        pack_id = str(pack.get("pack_id") or f"pack_{idx}")
        label = str(pack.get("label_ko") or pack_id)
        summary = str(pack.get("summary_ko") or "")
        excerpt = str(pack.get("card_excerpt_ko") or "")[:600]
        interpretation = summary
        if excerpt and excerpt not in interpretation:
            interpretation = f"{summary} {excerpt[:280]}".strip()
        verse_refs = _verse_refs(pack)
        anchors = verse_refs[:4]
        schools.append(
            {
                "school_tier": f"Pack {idx}",
                "interpretation_ko": interpretation,
                "citation_lock_anchors": anchors,
                "verse_refs": verse_refs or anchors,
                "traditions": [pack_id, "MKM reading pack"],
                "labels": ["research_only", "NON_GATING", "why_question_assembled=false"],
            }
        )
    return {
        "schema": f"{conflict_group_id.lower()}_studio_conflict_surface_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "source": Path(doc.get("_source_path") or "reading_pack_slice").name,
        "groups": [
            {
                "conflict_group_id": conflict_group_id,
                "lexicon_base": lexicon_base,
                "school_count": len(schools),
                "schools": schools,
            }
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reading-pack", type=Path, required=True)
    ap.add_argument("--conflict-group-id", required=True)
    ap.add_argument("--lexicon-base", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not args.reading_pack.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {args.reading_pack}"}), file=sys.stderr)
        return 2
    doc = json.loads(args.reading_pack.read_text(encoding="utf-8-sig"))
    doc["_source_path"] = str(args.reading_pack)
    out_doc = build_from_reading_pack(
        doc,
        conflict_group_id=args.conflict_group_id,
        lexicon_base=args.lexicon_base,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_path = args.out.resolve()
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path.relative_to(ROOT.resolve())).replace("\\", "/"),
                "school_count": out_doc["groups"][0]["school_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
