#!/usr/bin/env python3
"""Build A4-style Logos Studio synthesis bundle from reading pack + citation shard (P7, no CSS).

  py scripts/build_logos_studio_a4_synthesis_bundle_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

READING = ROOT / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"
CITATION = ROOT / "docs/final/artifacts/logos_studio_verse_citation_shard_v1_latest.json"
INSIGHT = ROOT / "docs/final/artifacts/showroom_qa_node_insight_cards_v1_latest.json"
PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_studio_a4_synthesis_bundle_v1_latest.json"
OUT_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/a4_synthesis_bundle_v1.json"

SECTION_MIN_CHARS = 280
VERSE_BODY_CAP = 400


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _trim(text: str, cap: int) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) <= cap:
        return s
    return s[: cap - 1].rstrip() + "…"


def _section_from_stage(stage: dict, citation_verses: dict, insight_cards: dict) -> dict:
    refs = [canonical_verse_ref(str(r)) for r in (stage.get("verse_refs") or [])]
    bodies: list[dict] = []
    for ref in refs:
        v = citation_verses.get(ref)
        if not v:
            continue
        bodies.append({"ref": ref, "text_ko": _trim(str(v.get("text_ko") or ""), VERSE_BODY_CAP)})
    excerpt = _trim(str(stage.get("excerpt_ko") or stage.get("summary_ko") or stage.get("bottleneck_ko") or ""), 900)
    if len(excerpt) < 80:
        for ref in refs:
            for card in (insight_cards or {}).values():
                if card.get("ref") == ref or str(card.get("ref") or "").endswith(ref):
                    excerpt = _trim(str(card.get("excerpt_ko") or ""), 900)
                    if excerpt:
                        break
            if len(excerpt) >= 80:
                break
    bottleneck = _trim(str(stage.get("bottleneck_ko") or ""), 220)
    block = {
        "stage_id": stage.get("stage_id"),
        "title_ko": stage.get("label_ko") or stage.get("stage_id"),
        "bottleneck_ko": bottleneck or None,
        "narrative_excerpt_ko": excerpt,
        "verse_bodies": bodies,
        "char_count": len(excerpt) + sum(len(b["text_ko"]) for b in bodies),
    }
    return block


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reading", type=Path, default=READING)
    ap.add_argument("--citation", type=Path, default=CITATION)
    ap.add_argument("--insight", type=Path, default=INSIGHT)
    ap.add_argument("--presets", type=Path, default=PRESETS)
    ap.add_argument("--min-section-chars", type=int, default=SECTION_MIN_CHARS)
    args = ap.parse_args()

    reading = _load(args.reading) if args.reading.is_file() else {}
    citation = _load(args.citation) if args.citation.is_file() else {}
    presets_doc = _load(args.presets) if args.presets.is_file() else {}
    insight_doc = _load(args.insight) if args.insight.is_file() else {}
    insight_cards = insight_doc.get("cards") or {}

    citation_verses = citation.get("verses") or {}
    sections: list[dict] = []
    for stage in reading.get("narrative_route_public") or []:
        sec = _section_from_stage(stage, citation_verses, insight_cards)
        if sec["char_count"] >= args.min_section_chars or sec["verse_bodies"] or sec.get("narrative_excerpt_ko"):
            sections.append(sec)

    preset_summaries = []
    for p in (presets_doc.get("presets") or [])[:12]:
        preset_summaries.append(
            {
                "id": p.get("id"),
                "prompt_ko": _trim(str(p.get("prompt_ko") or ""), 120),
                "answer_excerpt_ko": _trim(str(p.get("answer_ko") or ""), 200),
            }
        )

    total_chars = sum(s["char_count"] for s in sections)
    doc = {
        "schema_version": "logos_studio_a4_synthesis_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "governance_ko": "[HYPO][NON_GATING] A4 합성 번들 — 신학·인과 단답·Track A 근거 아님.",
        "reading_pack_id": reading.get("reading_pack_id") or "job_suffering_reason",
        "section_count": len(sections),
        "total_char_count": total_chars,
        "citation_verse_count": len(citation_verses),
        "sections": sections,
        "preset_spine_sample": preset_summaries,
        "reproducible_command": "py scripts/build_logos_studio_a4_synthesis_bundle_v1.py",
    }

    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUB.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_PUB.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "sections": len(sections), "total_chars": total_chars, "out": str(OUT_PUB)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
