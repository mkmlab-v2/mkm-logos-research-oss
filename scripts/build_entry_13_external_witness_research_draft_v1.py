#!/usr/bin/env python3
"""Web-sourced [HYPO] draft for ENTRY_13 intake — approve_promotion stays false."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAP_4Q = ROOT / "reports/dss_4q_ps5_line_witness_map_v1_latest.json"
OUT_RESEARCH = ROOT / "reports/entry_13_external_witness_research_draft_v1_latest.json"
OUT_DRAFT = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.draft.json"
OUT_MD = ROOT / "reports/entry_13_external_witness_research_draft_v1_latest.md"

EXTERNAL_REFS = [
    {
        "source_id": "qumran_digital_4q98b",
        "title": "4Q98b transcription",
        "url": "https://lexicon.qumran-digital.org/transcriptions/4Q98b/2025-03-11/index.html",
        "citation": "frg.1 lines 1-5; transcription links Ps 5:8-13 (Hebrew versification in QD)",
    },
    {
        "source_id": "qumran_digital_4q83",
        "title": "4Q83 transcription",
        "url": "https://lexicon.qumran-digital.org/transcriptions/4Q83/2025-03-11/index.html",
        "citation": "frg.1 cols 1-4; Ps 5:9-13 portions in prose layout",
    },
    {
        "source_id": "dss_english_4q98b",
        "title": "DSS English Bible 4Q98b",
        "url": "https://dssenglishbible.com/scroll4Q98b.htm",
        "citation": "Contents: Psalms 5:7-6:1 (English v. numbering)",
    },
    {
        "source_id": "djd_xvi_pointer",
        "title": "DJD XVI (Ulrich et al.)",
        "url": "https://www.academia.edu/33659314/Were_the_Psalms_Collections_at_Qumran_True_Psalters",
        "citation": "Secondary pointer — primary edition: DJD XVI Psalms to Chronicles",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _best_4q98b_witness(m: dict[str, Any]) -> dict[str, Any] | None:
    rows = [w for w in m.get("witnesses") or [] if str(w.get("scroll")) == "4Q98b"]
    if not rows:
        return None
    return max(rows, key=lambda w: float(w.get("mapping_score") or 0))


def build() -> dict[str, Any]:
    m4 = _load(MAP_4Q)
    best = _best_4q98b_witness(m4) or {}
    draft_intake = {
        "schema": "entry_12_13_external_witness_intake_v1",
        "version": "1.1.0-draft",
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "draft_status": "commander_review_required",
        "instructions": (
            "DRAFT ONLY — copy to entry_12_13_external_witness_v1.json after commander verifies "
            "verse-line crosswalk. Never set approve_promotion=true without primary transcription proof."
        ),
        "witness_promotions": [
            {
                "entry_id": "ENTRY_12",
                "canon_verse_id": "Ps.4.6",
                "witness_id": "none",
                "scroll": "mt_only",
                "line": "n/a",
                "edition_ref": "BHS/MT",
                "evidence_url": "",
                "evidence_note": "11Q5 bench retired; no Qumran Hebrew witness for Ps.4.6",
                "approve_promotion": False,
            },
            {
                "entry_id": "ENTRY_13",
                "canon_verse_id": "Ps.5.2",
                "witness_id": str(best.get("witness_id") or "dss_etcbc_line_XXXXXXX"),
                "scroll": "4Q98b",
                "fragment": "frg.1",
                "line": str(best.get("line") or "1"),
                "edition_ref": "Ulrich et al., DJD XVI (4QPss); Qumran-Digital 4Q98b 2025-03-11",
                "evidence_url": EXTERNAL_REFS[0]["url"],
                "evidence_note": (
                    "[HYPO draft] Public transcriptions place Ps 5:8-13 on 4Q98b frg.1 — NOT a confirmed "
                    "MT Ps.5.2 (v.2) line anchor. Local ETCBC row is provisional_lexical_anchor only."
                ),
                "external_verse_scope": "Ps 5:8-13 (QD Hebrew numbering)",
                "mt_ps_5_2_crosswalk_gap": True,
                "local_mapping_status": best.get("mapping_status"),
                "local_mapping_score": best.get("mapping_score"),
                "approve_promotion": False,
            },
        ],
    }
    return {
        "schema": "entry_13_external_witness_research_draft_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "promotion_ok": False,
        "external_refs": EXTERNAL_REFS,
        "scholarly_gap": {
            "entry_canon_target": "Ps.5.2",
            "external_fragment_scope": "Ps 5:8-13 on 4Q98b / portions on 4Q83",
            "implication": "Commander must adjudicate whether ENTRY_13 target verse should be relabeled or crosswalked",
        },
        "recommended_local_witness": best,
        "draft_intake_path": str(OUT_DRAFT.relative_to(ROOT)).replace("\\", "/"),
        "draft_intake": draft_intake,
        "reproduce": "py scripts/build_entry_13_external_witness_research_draft_v1.py",
    }


def render_md(doc: dict[str, Any]) -> str:
    gap = doc.get("scholarly_gap") or {}
    lines = [
        "# ENTRY_13 External Witness Research Draft [HYPO]",
        "",
        f"- Generated: {doc.get('generated_at_utc')}",
        "- **SEND_GATE: HOLD** · `approve_promotion: false`",
        "",
        "## Scholarly gap (Fact-Lock)",
        "",
        f"- Canon target: **{gap.get('entry_canon_target')}**",
        f"- External fragment scope: **{gap.get('external_fragment_scope')}**",
        f"- Implication: {gap.get('implication')}",
        "",
        "## External references",
        "",
    ]
    for r in doc.get("external_refs") or []:
        lines.append(f"- [{r.get('title')}]({r.get('url')}) — {r.get('citation')}")
    lines.extend(
        [
            "",
            "## Draft intake",
            "",
            f"- Path: `{doc.get('draft_intake_path')}`",
            "- Commander: verify verse-line crosswalk before copying to `entry_12_13_external_witness_v1.json`",
            "",
            "---",
            "Reproduce: `py scripts/build_entry_13_external_witness_research_draft_v1.py`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--research-out", type=Path, default=OUT_RESEARCH)
    ap.add_argument("--draft-out", type=Path, default=OUT_DRAFT)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()

    doc = build()
    args.research_out.parent.mkdir(parents=True, exist_ok=True)
    args.draft_out.parent.mkdir(parents=True, exist_ok=True)
    args.research_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.draft_out.write_text(
        json.dumps(doc["draft_intake"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "draft": str(args.draft_out.relative_to(ROOT)),
                "mt_ps_5_2_crosswalk_gap": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
