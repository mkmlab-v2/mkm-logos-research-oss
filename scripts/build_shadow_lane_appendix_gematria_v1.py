#!/usr/bin/env python3
"""Export DSS/Apocrypha gematria to isolated appendix SSOT (no canon 31k/41k write) [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.core.gematria_engine import build_gematria_metadata

FUSION = ROOT / "data/logos/manuscripts/fusion_unified_corpus_stage1_v1.jsonl"
DSS_JSONL = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
APO_MANIFEST = ROOT / "docs/final/artifacts/logos_apocrypha_bootstrap_manifest_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/shadow_lane_appendix_gematria_v1_latest.json"

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
GREEK_RE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _gematria_from_text(text: str) -> dict[str, int]:
    t = (text or "").strip()
    meta = build_gematria_metadata(raw_text=t, compressed_text=t, reconstructed_text=t)
    return {
        "hebrew_value": int(meta.get("raw_hebrew_sum") or 0),
        "greek_value": int(meta.get("raw_greek_sum") or 0),
        "combined_value": int(meta.get("raw_combined_sum") or 0),
        "hebrew_chars": int(meta.get("raw_hebrew_chars") or 0),
        "greek_chars": int(meta.get("raw_greek_chars") or 0),
    }


def _row(
    *,
    entry_id: str,
    lane: str,
    source: str,
    text: str,
    gematria: dict[str, Any],
    provenance: str,
    source_ref: str = "",
) -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "lane": lane,
        "source": source,
        "source_ref": source_ref or entry_id,
        "text_preview": (text or "")[:120],
        "gematria": gematria,
        "provenance": provenance,
        "non_gating": True,
        "research_only": True,
    }


def _from_fusion(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            lane = str(doc.get("lane") or "")
            if lane not in ("dss", "apocrypha"):
                continue
            g = doc.get("gematria") or {}
            rows.append(
                _row(
                    entry_id=str(doc.get("row_id") or doc.get("source_ref") or ""),
                    lane=lane,
                    source=str(doc.get("source") or "fusion_unified"),
                    text=str(doc.get("text") or ""),
                    gematria={
                        "hebrew_value": int(g.get("raw_hebrew_sum") or 0),
                        "greek_value": int(g.get("raw_greek_sum") or 0),
                        "combined_value": int(g.get("raw_combined_sum") or 0),
                        "hebrew_chars": int(g.get("raw_hebrew_chars") or 0),
                        "greek_chars": int(g.get("raw_greek_chars") or 0),
                    },
                    provenance="fusion_unified_corpus_stage1_v1",
                    source_ref=str(doc.get("source_ref") or ""),
                )
            )
    return rows


def _from_apocrypha_fixture(path: Path, seen: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            vid = str(doc.get("verse_id") or "")
            if not vid or vid in seen:
                continue
            text = str(doc.get("original_text") or "")
            if not GREEK_RE.search(text) and not HEBREW_RE.search(text):
                continue
            seen.add(vid)
            g = _gematria_from_text(text)
            rows.append(
                _row(
                    entry_id=vid,
                    lane="apocrypha",
                    source="apocrypha_fixture",
                    text=text,
                    gematria=g,
                    provenance="apocrypha_original_only_latest.jsonl",
                    source_ref=vid,
                )
            )
    return rows


def _from_dss_shadow(path: Path, seen: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            eid = str(doc.get("id") or "")
            if not eid or eid in seen:
                continue
            text = str(doc.get("text") or "")
            seen.add(eid)
            g = _gematria_from_text(text)
            rows.append(
                _row(
                    entry_id=eid,
                    lane="dss",
                    source="dss_parsed_enriched",
                    text=text,
                    gematria=g,
                    provenance="dss_parsed_enriched.jsonl",
                    source_ref=eid,
                )
            )
    return rows


def build() -> dict[str, Any]:
    fusion_rows = _from_fusion(FUSION)
    seen = {r["entry_id"] for r in fusion_rows}
    manifest = _load_json(APO_MANIFEST)
    apo_path = ROOT / str(manifest.get("output_jsonl") or "data/logos/manuscripts/apocrypha_original_only_latest.jsonl")
    apo_rows = _from_apocrypha_fixture(apo_path, seen)
    seen.update(r["entry_id"] for r in apo_rows)
    dss_rows = _from_dss_shadow(DSS_JSONL, seen)

    all_rows = fusion_rows + apo_rows + dss_rows
    by_lane: dict[str, int] = {}
    for r in all_rows:
        by_lane[r["lane"]] = by_lane.get(r["lane"], 0) + 1

    return {
        "schema": "shadow_lane_appendix_gematria_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "logos_core_mutation_forbidden": True,
            "merge_into_canon_31k_41k": False,
            "track_a_bridge": False,
            "ms_headline_merge_forbidden": True,
        },
        "inputs": {
            "fusion_jsonl": str(FUSION.relative_to(ROOT)).replace("\\", "/"),
            "dss_jsonl": str(DSS_JSONL.relative_to(ROOT)).replace("\\", "/"),
            "apocrypha_jsonl": str(apo_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "summary": {
            "total_rows": len(all_rows),
            "by_lane": by_lane,
            "from_fusion": len(fusion_rows),
            "from_apocrypha_fixture": len(apo_rows),
            "from_dss_shadow_compute": len(dss_rows),
        },
        "rows": all_rows,
        "reproduce": "py scripts/build_shadow_lane_appendix_gematria_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    ok = int(sm.get("total_rows") or 0) >= 100
    print(
        json.dumps(
            {
                "ok": ok,
                "total_rows": sm.get("total_rows"),
                "by_lane": sm.get("by_lane"),
                "out": str(args.out.relative_to(ROOT)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
