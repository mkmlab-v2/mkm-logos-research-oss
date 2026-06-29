#!/usr/bin/env python3
"""Canon verse ↔ shadow appendix gematria xref (overlap only, read-only map) [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.shadow_lane_gematria_common_v1 import (
    VERSE_REF_RE,
    audit_class_for_shadow,
    build_appendix_index,
    load_dss_enriched_by_id,
    load_json,
    numeric_comparison_eligible,
    resolve_shadow_entry,
)

DSS_ALIGN = ROOT / "reports/dss_shadow_alignment_v1_latest.json"
CANON_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"
APPENDIX = ROOT / "reports/shadow_lane_appendix_gematria_v1_latest.json"
DSS_JSONL = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
WITNESS_REGISTRY = ROOT / "reports/shadow_line_witness_registry_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/shadow_canon_gematria_xref_map_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon_gematria(jsonl: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not jsonl.is_file():
        return out
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            g = row.get("gematria_v1") or {}
            if vid:
                out[vid] = {
                    "hebrew_value": int(g.get("hebrew_value") or 0),
                    "greek_value": int(g.get("greek_value") or 0),
                    "total_value": int(g.get("total_value") or 0),
                }
    return out


def _dss_rows_citing_verse(vid: str) -> list[str]:
    ids: list[str] = []
    if not DSS_JSONL.is_file():
        return ids
    with DSS_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = str(row.get("text") or "")
            if vid in text or any(m.group(0) == vid for m in VERSE_REF_RE.finditer(text)):
                rid = str(row.get("id") or "")
                if rid:
                    ids.append(rid)
    return sorted(set(ids))


def _line_witness_by_verse(registry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in registry.get("rows") or []:
        vid = str(row.get("canon_verse_id") or "")
        if not vid:
            continue
        out.setdefault(vid, []).append(row)
    return out


def build() -> dict[str, Any]:
    align = load_json(DSS_ALIGN)
    appendix = load_json(APPENDIX)
    registry = load_json(WITNESS_REGISTRY)
    appendix_index = build_appendix_index(appendix)
    dss_by_id = load_dss_enriched_by_id()
    canon_g = _canon_gematria(CANON_JSONL)
    line_witness = _line_witness_by_verse(registry)

    overlap_verses = [v for v, _ in (align.get("phase_p1_canon_overlap") or {}).get("top_cited_verses") or []]
    links: list[dict[str, Any]] = []
    resolved_samples = 0
    line_witness_samples = 0
    for vid in overlap_verses:
        canon = canon_g.get(vid)
        if not canon:
            continue
        shadow_ids = _dss_rows_citing_verse(vid)
        shadow_gematria: list[dict[str, Any]] = []
        for sid in shadow_ids[:12]:
            resolved = resolve_shadow_entry(sid, appendix_index, dss_by_id)
            if not resolved:
                continue
            g = resolved.get("gematria") or {}
            preview = str(resolved.get("text_preview") or "")
            audit_class = audit_class_for_shadow(g, preview)
            shadow_gematria.append(
                {
                    **resolved,
                    "audit_class": audit_class,
                    "numeric_comparison_eligible": numeric_comparison_eligible(audit_class, g),
                    "hebrew_delta_vs_canon": int(g.get("hebrew_value") or 0) - int(canon.get("hebrew_value") or 0)
                    if numeric_comparison_eligible(audit_class, g)
                    else None,
                }
            )
            resolved_samples += 1
        lw_rows = line_witness.get(vid) or []
        line_witness_samples += len(lw_rows)
        links.append(
            {
                "canon_verse_id": vid,
                "canon_gematria": canon,
                "shadow_entry_ids": shadow_ids[:24],
                "shadow_gematria_samples": shadow_gematria,
                "line_witness_samples": lw_rows[:8],
                "xref_type": "dss_text_citation_overlap",
                "writes_canon": False,
            }
        )

    return {
        "schema": "shadow_canon_gematria_xref_map_v1",
        "version": "1.2.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
            "track_a_bridge": False,
        },
        "summary": {
            "overlap_verse_candidates": len(overlap_verses),
            "mapped_links": len(links),
            "appendix_rows_indexed": len(appendix_index),
            "resolved_shadow_samples": resolved_samples,
            "links_with_samples": sum(1 for lnk in links if lnk.get("shadow_gematria_samples")),
            "line_witness_samples": line_witness_samples,
            "line_witness_verses": sum(1 for lnk in links if lnk.get("line_witness_samples")),
        },
        "links": links,
        "reproduce": "py scripts/build_shadow_canon_gematria_xref_map_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("mapped_links") or 0) >= 1 and int(sm.get("resolved_shadow_samples") or 0) >= 9
    print(json.dumps({"ok": ok, "summary": sm, "out": str(args.out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
