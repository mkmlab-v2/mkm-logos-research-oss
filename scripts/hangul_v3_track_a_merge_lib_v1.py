#!/usr/bin/env python3
"""Track A merge helpers — production 41708 base + v2/v3 overlay union (preflight only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _form_key(form: str) -> str:
    form = str(form or "").strip()
    return form.lower() if form.isascii() else form


def ko_forms(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for ent in doc.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        lang = str(ent.get("lang") or "").lower()
        aid = str(ent.get("atom_id") or "")
        if lang == "ko" or aid.startswith("hangul_curated"):
            form = str(ent.get("normalized_form") or "").strip()
            if form:
                out.add(_form_key(form))
    return out


def count_ko(doc: dict[str, Any]) -> int:
    return len(ko_forms(doc))


def row_count(doc: dict[str, Any]) -> int:
    return int(doc.get("row_count") or len(doc.get("entries") or []))


def subset_audit(production: dict[str, Any], v3: dict[str, Any]) -> dict[str, Any]:
    prod_ko = ko_forms(production)
    v3_ko = ko_forms(v3)
    v3_only = sorted(v3_ko - prod_ko)
    prod_only = sorted(prod_ko - v3_ko)
    return {
        "production_ko_count": len(prod_ko),
        "v3_ko_count": len(v3_ko),
        "intersect_count": len(prod_ko & v3_ko),
        "v3_only_count": len(v3_only),
        "prod_only_count": len(prod_only),
        "v3_is_subset_of_production": len(v3_only) == 0,
        "naive_v3_swap_regresses_ko": len(prod_only) > 0,
        "prod_only_sample": prod_only[:12],
        "v3_only_sample": v3_only[:12],
    }


def v3_manifest_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in manifest.get("lemmas") or []:
        if not isinstance(row, dict):
            continue
        form = str(row.get("form") or "").strip()
        if form:
            out[_form_key(form)] = row
    return out


def enrich_v3_golden40_metadata(
    entries: list[dict[str, Any]],
    v3_manifest: dict[str, Any],
) -> dict[str, Any]:
    idx = v3_manifest_index(v3_manifest)
    touched: list[str] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        lang = str(ent.get("lang") or "").lower()
        if lang != "ko":
            continue
        form = str(ent.get("normalized_form") or "").strip()
        meta = idx.get(_form_key(form))
        if not meta:
            continue
        ent["v3_golden40_evidence"] = {
            "golden40_case_hit_count": meta.get("golden40_case_hit_count"),
            "tier": meta.get("tier"),
            "source": meta.get("source"),
            "wave": v3_manifest.get("wave"),
        }
        touched.append(form)
    return {"enriched_ko_forms": touched, "enriched_count": len(touched)}


def build_production_union_v2_on_base(
    *,
    production_path: Path,
    manifest_path: Path,
    v3_manifest_path: Path | None = None,
    enrich_v3: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from scripts.build_master_codebook_hangul_curated_overlay_v1 import build_from_manifest

    production_path = production_path.resolve()
    manifest_path = manifest_path.resolve()
    out_path = production_path.parent / (
        "master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v3_track_a_merge_preflight.json"
    )
    overlay_meta = build_from_manifest(manifest_path, production_path, out_path)
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    v3_enrich: dict[str, Any] = {"enriched_count": 0}
    if enrich_v3 and v3_manifest_path and v3_manifest_path.is_file():
        v3_manifest = json.loads(v3_manifest_path.read_text(encoding="utf-8"))
        v3_enrich = enrich_v3_golden40_metadata(list(doc.get("entries") or []), v3_manifest)
        doc["entries"] = list(doc.get("entries") or [])
    production = json.loads(production_path.read_text(encoding="utf-8"))
    doc["generated_at_utc"] = _utc()
    doc["export_candidate_meta"] = {
        "schema": "hangul_v3_track_a_merge_export_candidate_v1",
        "merge_profile": "production_union_v2_full_on_base",
        "research_only": True,
        "track_a_active_write": False,
        "production_ssot_swap": False,
        "promotion": "HOLD",
        "base_production_lexicon": _rel(production_path),
        "source_manifest": _rel(manifest_path),
        "v3_golden40_manifest": _rel(v3_manifest_path) if v3_manifest_path and v3_manifest_path.is_file() else None,
        "overlay_build": overlay_meta,
        "v3_metadata_enrichment": v3_enrich,
        "production_ko_count": count_ko(production),
        "candidate_ko_count": count_ko(doc),
        "ko_delta_vs_production": count_ko(doc) - count_ko(production),
    }
    doc["row_count"] = len(doc.get("entries") or [])
    out_path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    audit = subset_audit(production, doc)
    build_report = {
        "schema": "hangul_v3_track_a_merge_candidate_build_v1",
        "generated_at_utc": _utc(),
        "merge_profile": "production_union_v2_full_on_base",
        "candidate_path": _rel(out_path),
        "production_path": _rel(production_path),
        "production_rows": row_count(production),
        "candidate_rows": row_count(doc),
        "production_ko": count_ko(production),
        "candidate_ko": count_ko(doc),
        "subset_audit": audit,
        "overlay_meta": overlay_meta,
        "v3_metadata_enrichment": v3_enrich,
    }
    return doc, build_report


def build_production_preserve_v3_metadata_refresh(
    *,
    production_path: Path,
    v3_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    production_path = production_path.resolve()
    v3_manifest_path = v3_manifest_path.resolve()
    production = json.loads(production_path.read_text(encoding="utf-8"))
    v3_manifest = json.loads(v3_manifest_path.read_text(encoding="utf-8"))
    entries = [dict(e) for e in production.get("entries") or [] if isinstance(e, dict)]
    v3_enrich = enrich_v3_golden40_metadata(entries, v3_manifest)
    doc = dict(production)
    doc["entries"] = entries
    doc["generated_at_utc"] = _utc()
    doc["row_count"] = len(entries)
    doc["export_candidate_meta"] = {
        "schema": "hangul_v3_track_a_merge_export_candidate_v1",
        "merge_profile": "production_preserve_v3_metadata_refresh",
        "research_only": True,
        "track_a_active_write": False,
        "production_ssot_swap": False,
        "promotion": "HOLD",
        "note": "Row-preserving metadata refresh only; no ko loss vs production",
        "v3_metadata_enrichment": v3_enrich,
        "production_ko_count": count_ko(production),
        "candidate_ko_count": count_ko(doc),
    }
    return doc, {
        "merge_profile": "production_preserve_v3_metadata_refresh",
        "production_ko": count_ko(production),
        "candidate_ko": count_ko(doc),
        "subset_audit": subset_audit(production, doc),
        "v3_metadata_enrichment": v3_enrich,
    }
