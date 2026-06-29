#!/usr/bin/env python3
"""Enrich Logos motif registry gematria_texts from 31102 verse corpus (HG-4 / max advancement).

Updates:
  docs/final/artifacts/logos_motif_corpus_enriched_overlay_v1.json
  docs/final/artifacts/logos_motif_human_gate_extensions_v1.json (patch gematria fields)
  docs/final/artifacts/logos_motif_corpus_enrichment_report_v1_latest.json

Reproducible:
  py scripts/enrich_logos_motif_gematria_from_corpus_v1.py
  py scripts/run_logos_max_advancement_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_verse_corpus_lookup_v1 import (
    DEFAULT_CORPUS,
    extract_reconstructed_clause,
    load_corpus_index,
    lookup_verse,
    normalize_verse_ref,
)

REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
EXTENSIONS = ROOT / "docs/final/artifacts/logos_motif_human_gate_extensions_v1.json"
EXPANSION = ROOT / "docs/final/artifacts/logos_corpus_expansion_extensions_v1.json"
OVERLAY = ROOT / "docs/final/artifacts/logos_motif_corpus_enriched_overlay_v1.json"
REPORT = ROOT / "docs/final/artifacts/logos_motif_corpus_enrichment_report_v1_latest.json"


def _lemma_text(spec: dict[str, Any]) -> str:
    lemma = spec.get("motif_lemma") or {}
    return str(lemma.get("greek") or lemma.get("hebrew") or spec.get("gematria_text") or "")


def enrich_spec(spec: dict[str, Any], *, corpus_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    verse_refs = spec.get("verse_refs") or []
    if not verse_refs:
        return spec, {"status": "skip_no_verse", "slot_id": spec.get("slot_id")}
    ref = str(verse_refs[0])
    hit = lookup_verse(ref, corpus_path=corpus_path)
    lemma = _lemma_text(spec)
    if hit is None:
        return spec, {
            "status": "miss",
            "slot_id": spec.get("slot_id"),
            "verse_ref": ref,
            "canon_ref": normalize_verse_ref(ref),
        }
    raw = hit["raw"]
    compressed = lemma or spec.get("gematria_text") or raw
    reconstructed = extract_reconstructed_clause(raw, lemma) if lemma else raw
    enriched = dict(spec)
    enriched["gematria_text"] = compressed
    enriched["gematria_texts"] = {
        "raw": raw,
        "compressed": compressed,
        "reconstructed": reconstructed,
    }
    enriched["corpus_enrichment_v1"] = {
        "corpus_verse_id": hit["verse_id"],
        "registry_verse_ref": ref,
        "unit": "verse",
        "pipeline3_total": hit.get("pipeline3_total"),
        "source": "verse_4pipeline_full_31102",
    }
    if enriched.get("source") == "human_gate_queue_v1_merged":
        enriched["source"] = "human_gate_queue_v1_corpus_enriched"
    return enriched, {
        "status": "hit",
        "slot_id": spec.get("slot_id"),
        "verse_ref": ref,
        "corpus_verse_id": hit["verse_id"],
        "raw_len": len(raw),
        "lemma": lemma,
    }


def enrich_all(
    *,
    corpus_path: Path = DEFAULT_CORPUS,
    registry_path: Path = REGISTRY,
    extensions_path: Path = EXTENSIONS,
    overlay_path: Path = OVERLAY,
    only_minimal: bool = True,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not corpus_path.is_file():
        raise SystemExit(f"Missing corpus: {corpus_path}")
    load_corpus_index(str(corpus_path.resolve()))

    targets: list[dict[str, Any]] = []
    if registry_path.is_file():
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        for e in reg.get("entries", []):
            if not e.get("enabled"):
                continue
            if not only_minimal:
                targets.append(dict(e))
                continue
            if e.get("corpus_enrichment_v1"):
                continue
            texts = e.get("gematria_texts") or {}
            raw = str(texts.get("raw") or "")
            comp = str(texts.get("compressed") or "")
            if raw == comp and len(raw) < 80:
                targets.append(dict(e))

    overlay_entries: dict[str, dict[str, Any]] = {}
    if overlay_path.is_file():
        prev = json.loads(overlay_path.read_text(encoding="utf-8"))
        for e in prev.get("entries", []):
            sid = e.get("slot_id")
            if sid:
                overlay_entries[sid] = dict(e)
    per_slot: list[dict[str, Any]] = []
    hits = misses = skips = 0

    for spec in targets:
        enriched, meta = enrich_spec(spec, corpus_path=corpus_path)
        per_slot.append(meta)
        sid = str(spec.get("slot_id") or "")
        if meta["status"] == "hit":
            hits += 1
            patch = {
                "slot_id": sid,
                "gematria_text": enriched["gematria_text"],
                "gematria_texts": enriched["gematria_texts"],
                "corpus_enrichment_v1": enriched["corpus_enrichment_v1"],
            }
            if spec.get("source"):
                patch["source"] = enriched.get("source", spec["source"])
            overlay_entries[sid] = patch
        elif meta["status"] == "miss":
            misses += 1
        else:
            skips += 1

    ext_patched = 0
    if extensions_path.is_file():
        ext_doc = json.loads(extensions_path.read_text(encoding="utf-8"))
        new_entries: list[dict[str, Any]] = []
        for e in ext_doc.get("entries", []):
            sid = e.get("slot_id")
            if sid in overlay_entries:
                merged = dict(e)
                merged.update(overlay_entries[sid])
                new_entries.append(merged)
                ext_patched += 1
            else:
                new_entries.append(e)
        ext_doc["entries"] = new_entries
        ext_doc["corpus_enriched_at_utc"] = generated_at_utc
        extensions_path.write_text(json.dumps(ext_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exp_patched = 0
    if EXPANSION.is_file():
        exp_doc = json.loads(EXPANSION.read_text(encoding="utf-8"))
        new_entries = []
        for e in exp_doc.get("entries", []):
            sid = e.get("slot_id")
            if sid in overlay_entries:
                merged = dict(e)
                merged.update(overlay_entries[sid])
                merged["source"] = "corpus_expansion_wave_v1_corpus_enriched"
                new_entries.append(merged)
                exp_patched += 1
            else:
                new_entries.append(e)
        exp_doc["entries"] = new_entries
        exp_doc["corpus_enriched_at_utc"] = generated_at_utc
        EXPANSION.write_text(json.dumps(exp_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    overlay_doc = {
        "schema": "logos_motif_corpus_enriched_overlay_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "corpus_path": corpus_path.relative_to(ROOT).as_posix(),
        "entry_count": len(overlay_entries),
        "entries": [overlay_entries[k] for k in sorted(overlay_entries.keys())],
        "reproducible_command": "py scripts/enrich_logos_motif_gematria_from_corpus_v1.py",
    }
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(json.dumps(overlay_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "logos_motif_corpus_enrichment_report_v1",
        "generated_at_utc": generated_at_utc,
        "targets": len(targets),
        "hits": hits,
        "misses": misses,
        "skips": skips,
        "hit_rate": round(hits / len(targets), 4) if targets else 0.0,
        "extensions_patched": ext_patched,
        "expansion_patched": exp_patched,
        "only_minimal": only_minimal,
        "per_slot": per_slot,
        "overlay_path": overlay_path.relative_to(ROOT).as_posix(),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--all-enabled", action="store_true", help="Re-enrich all enabled, not only minimal")
    args = parser.parse_args()
    report = enrich_all(corpus_path=args.corpus, only_minimal=not args.all_enabled)
    print(f"WROTE: {OVERLAY}")
    print(f"WROTE: {REPORT}")
    print(f"  hits={report['hits']}/{report['targets']} miss={report['misses']} rate={report['hit_rate']}")
    if report["targets"] == 0 and report["hits"] == 0:
        return 0
    if report["misses"] <= 1 and report.get("hit_rate", 0) >= 0.99:
        return 0
    return 0 if report["misses"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
