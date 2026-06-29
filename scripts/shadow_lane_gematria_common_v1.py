"""Shared helpers for shadow-lane gematria appendix / xref / audit [HYPO]."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.core.gematria_engine import build_gematria_metadata

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
GREEK_RE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
VERSE_REF_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9]{0,8})\.(\d+)\.(\d+)\b")

DSS_JSONL = ROOT / "data/logos/manuscripts/dss_parsed_enriched.jsonl"
DSS_ORIGINAL = ROOT / "data/logos/manuscripts/dss_original_only_latest.jsonl"
APPENDIX = ROOT / "reports/shadow_lane_appendix_gematria_v1_latest.json"
FUSION = ROOT / "data/logos/manuscripts/fusion_unified_corpus_stage1_v1.jsonl"
CANON_JSONL = ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"


def gematria_from_text(text: str) -> dict[str, int]:
    t = (text or "").strip()
    meta = build_gematria_metadata(raw_text=t, compressed_text=t, reconstructed_text=t)
    return {
        "hebrew_value": int(meta.get("raw_hebrew_sum") or 0),
        "greek_value": int(meta.get("raw_greek_sum") or 0),
        "combined_value": int(meta.get("raw_combined_sum") or 0),
        "hebrew_chars": int(meta.get("raw_hebrew_chars") or 0),
        "greek_chars": int(meta.get("raw_greek_chars") or 0),
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def load_dss_enriched_by_id() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not DSS_JSONL.is_file():
        return out
    with DSS_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            eid = str(row.get("id") or "")
            if eid:
                out[eid] = row
    return out


def build_appendix_index(appendix_doc: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    doc = appendix_doc if appendix_doc is not None else load_json(APPENDIX)
    index: dict[str, dict[str, Any]] = {}
    for row in doc.get("rows") or []:
        eid = str(row.get("entry_id") or "")
        if eid:
            index[eid] = row
        src = str(row.get("source_ref") or "")
        if src and src not in index:
            index[src] = row
        if eid.startswith("dss:"):
            short = eid.split(":", 1)[-1]
            index.setdefault(short, row)
    return index


def resolve_shadow_entry(entry_id: str, appendix_index: dict[str, dict[str, Any]], dss_by_id: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    row = appendix_index.get(entry_id)
    if row:
        return {
            "shadow_entry_id": entry_id,
            "lane": row.get("lane"),
            "source": row.get("source"),
            "gematria": row.get("gematria") or {},
            "resolve_path": "appendix_index",
            "text_preview": row.get("text_preview") or "",
        }
    dss = dss_by_id.get(entry_id)
    if dss:
        g = gematria_from_text(str(dss.get("text") or ""))
        return {
            "shadow_entry_id": entry_id,
            "lane": "dss",
            "source": "dss_parsed_enriched",
            "gematria": g,
            "resolve_path": "dss_jsonl_fallback",
            "text_preview": str(dss.get("text") or "")[:120],
        }
    return None


def audit_class_for_shadow(gematria: dict[str, Any], text_preview: str) -> str:
    hc = int(gematria.get("hebrew_chars") or 0)
    gc = int(gematria.get("greek_chars") or 0)
    if hc >= 6:
        return "hebrew_witness_fragment"
    if gc >= 6:
        return "greek_witness_fragment"
    if VERSE_REF_RE.search(text_preview or ""):
        return "metadata_citation"
    return "metadata_only"


def numeric_comparison_eligible(audit_class: str, gematria: dict[str, Any]) -> bool:
    if audit_class == "hebrew_witness_fragment":
        return int(gematria.get("hebrew_chars") or 0) >= 6
    if audit_class == "greek_witness_fragment":
        return int(gematria.get("greek_chars") or 0) >= 6
    return False


def hebrew_tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u0590-\u05FF]+", text or ""))


def norm_hebrew(text: str) -> str:
    return re.sub(r"[^\u0590-\u05FF]", "", text or "")


def load_canon_verse(canon_verse_id: str) -> dict[str, Any] | None:
    if not CANON_JSONL.is_file():
        return None
    with CANON_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("verse_id") or "") != canon_verse_id:
                continue
            text = str((row.get("text_span") or {}).get("original_script_text") or "")
            g = row.get("gematria_v1") or {}
            return {
                "canon_verse_id": canon_verse_id,
                "text": text,
                "norm": norm_hebrew(text),
                "tokens": hebrew_tokens(text),
                "gematria": {
                    "hebrew_value": int(g.get("hebrew_value") or 0),
                    "greek_value": int(g.get("greek_value") or 0),
                    "total_value": int(g.get("total_value") or 0),
                },
            }
    return None


def mapping_status_for_score(score: float, lemma_hits: int) -> str:
    if score >= 0.85:
        return "verified_line_witness"
    if score >= 0.08 or lemma_hits >= 2:
        return "provisional_lexical_anchor"
    return "line_bucket_candidate"


def line_witness_numeric_eligible(
    *,
    gematria: dict[str, Any],
    mapping_status: str,
    scroll: str,
) -> bool:
    if scroll != "11Q5":
        return False
    if int(gematria.get("hebrew_chars") or 0) < 6:
        return False
    return mapping_status in ("verified_line_witness", "provisional_lexical_anchor")
