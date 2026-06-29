#!/usr/bin/env python3
"""Ingest scriptures-js STEP lexicon rows into gematria lookup JSONL [HYPO].

Lexicon lookup layer only — maps lemma gematria to S-L-K-M via gematria_bridge_v1.
No prophecy claims, no Track A promotion.
License gate: --ack-license-verify-upstream.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_scriptures_js_gematria_lib_v1 import (
    compute_gematria_for_lemma,
    language_from_strongs,
    normalize_strongs,
    slkm_vector_from_gematria,
)

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/logos_scriptures_js_gematria_ingest_v1_latest.json"
DEFAULT_SRC_DIR = ROOT / "storage/external_kg/scriptures_js_v1"
FIXTURE_DIR = ROOT / "tests/fixtures/scriptures_js_gematria_sample_v1"

LICENSE_ACK = "verify_upstream_mit_cc_by_4"
LEXICON_FILES = (
    ("stepbible-tbesh.json", "stepbible-tbesh"),
    ("stepbible-tbesg.json", "stepbible-tbesg"),
    ("stepbible-tflsj.json", "stepbible-tflsj"),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _load_lexicon(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"expected dict lexicon: {path}")
    return doc


def _entry_row(
    *,
    strongs: str,
    rec: dict[str, Any],
    lexicon_source: str,
    entry_i: int,
    license_tag: str,
) -> dict[str, Any] | None:
    lemma = str(rec.get("lemma") or "").strip()
    if not lemma:
        return None
    lang = language_from_strongs(strongs)
    prepared, gematria = compute_gematria_for_lemma(lemma, lang)
    if not prepared:
        return None
    slkm = slkm_vector_from_gematria(gematria, lang)
    return {
        "schema": "logos_scriptures_js_gematria_lexicon_entry_v1",
        "entry_id": f"scriptures_js_lex::{strongs}::{lexicon_source}",
        "strongs": strongs,
        "language": lang,
        "lexicon_source": lexicon_source,
        "lemma": lemma,
        "lemma_gematria_input": prepared,
        "transliteration": str(rec.get("transliteration") or ""),
        "gloss": str(rec.get("gloss") or "")[:512],
        "morphology": str(rec.get("morphology") or ""),
        "gematria": gematria,
        "vector_4d": slkm["vector_4d"],
        "gematria_metadata": slkm["gematria_metadata"],
        "kernel_recipe_id": slkm["kernel_recipe_id"],
        "lookup_only": True,
        "prophecy_claims": False,
        "hypothesis_tier": "B",
        "research_only": True,
        "source": "scriptures_js_gematria",
        "license": license_tag,
        "provenance": {
            "upstream_source": str(rec.get("source") or lexicon_source),
            "strongs_extended": rec.get("strongsExtended"),
            "strongs_unified": rec.get("strongsUnified"),
        },
        "entry_index": entry_i,
    }


def build_entries_from_lexicon_dir(
    src_dir: Path,
    *,
    max_entries: int,
    skip_tflsj: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lexicon_dir = src_dir / "lexicon" if (src_dir / "lexicon").is_dir() else src_dir
    stats: dict[str, Any] = {
        "files_scanned": 0,
        "rows_scanned": 0,
        "entries_built": 0,
        "skipped_bad_strongs": 0,
        "skipped_empty_lemma": 0,
        "by_lexicon": {},
    }
    rows: list[dict[str, Any]] = []
    entry_i = 0

    for fname, lexicon_source in LEXICON_FILES:
        if skip_tflsj and fname == "stepbible-tflsj.json":
            continue
        path = lexicon_dir / fname
        if not path.is_file():
            continue
        stats["files_scanned"] += 1
        lex_stats = {"rows_scanned": 0, "entries_built": 0}
        doc = _load_lexicon(path)
        for raw_strongs, rec in doc.items():
            stats["rows_scanned"] += 1
            lex_stats["rows_scanned"] += 1
            if len(rows) >= max_entries:
                break
            if not isinstance(rec, dict):
                continue
            strongs = normalize_strongs(str(raw_strongs))
            if not strongs:
                stats["skipped_bad_strongs"] += 1
                continue
            row = _entry_row(
                strongs=strongs,
                rec=rec,
                lexicon_source=lexicon_source,
                entry_i=entry_i,
                license_tag=LICENSE_ACK,
            )
            if row is None:
                stats["skipped_empty_lemma"] += 1
                continue
            rows.append(row)
            entry_i += 1
            stats["entries_built"] += 1
            lex_stats["entries_built"] += 1
        stats["by_lexicon"][lexicon_source] = lex_stats
        if len(rows) >= max_entries:
            break

    return rows, stats


def build_entries_from_fixture(
    fixture_dir: Path,
    *,
    max_entries: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats: dict[str, Any] = {
        "files_scanned": 0,
        "rows_scanned": 0,
        "entries_built": 0,
        "skipped_bad_strongs": 0,
        "skipped_empty_lemma": 0,
        "by_lexicon": {},
    }
    rows: list[dict[str, Any]] = []
    entry_i = 0
    for fname, lexicon_source in LEXICON_FILES[:2]:
        path = fixture_dir / fname
        if not path.is_file():
            continue
        stats["files_scanned"] += 1
        lex_stats = {"rows_scanned": 0, "entries_built": 0}
        doc = _load_lexicon(path)
        for raw_strongs, rec in doc.items():
            stats["rows_scanned"] += 1
            lex_stats["rows_scanned"] += 1
            if len(rows) >= max_entries:
                break
            strongs = normalize_strongs(str(raw_strongs))
            if not strongs:
                stats["skipped_bad_strongs"] += 1
                continue
            row = _entry_row(
                strongs=strongs,
                rec=rec if isinstance(rec, dict) else {},
                lexicon_source=lexicon_source,
                entry_i=entry_i,
                license_tag="fixture_offline_only",
            )
            if row is None:
                stats["skipped_empty_lemma"] += 1
                continue
            rows.append(row)
            entry_i += 1
            stats["entries_built"] += 1
            lex_stats["entries_built"] += 1
        stats["by_lexicon"][lexicon_source] = lex_stats
    return rows, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scriptures-js-dir", type=Path, default=None)
    ap.add_argument("--use-fixture-sample", action="store_true")
    ap.add_argument("--ack-license-verify-upstream", action="store_true")
    ap.add_argument("--skip-tflsj", action="store_true")
    ap.add_argument("--max-entries", type=int, default=300000)
    ap.add_argument("--min-entries", type=int, default=3)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if args.use_fixture_sample:
        rows, stats = build_entries_from_fixture(FIXTURE_DIR, max_entries=args.max_entries)
        src_dir = FIXTURE_DIR
        license_ack = "fixture_offline_only"
    elif args.scriptures_js_dir:
        if not args.ack_license_verify_upstream:
            raise SystemExit("non-fixture ingest requires --ack-license-verify-upstream")
        rows, stats = build_entries_from_lexicon_dir(
            args.scriptures_js_dir,
            max_entries=args.max_entries,
            skip_tflsj=args.skip_tflsj,
        )
        src_dir = args.scriptures_js_dir
        license_ack = LICENSE_ACK
    else:
        raise SystemExit("provide --scriptures-js-dir or --use-fixture-sample")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    manifest = {
        "schema": "logos_scriptures_js_gematria_lexicon_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "lookup_only": True,
        "prophecy_claims": False,
        "entry_count": len(rows),
        "kernel_recipe_id": "gematria_bridge_v1",
        "operational_4d_ssot": "gematria_bridge_v1 S-L-K-M",
        "stats": stats,
        "note": "STEPBible Strong lookup + gematria sums; attributed lookup only.",
        "reproduce": (
            "py scripts/ingest_logos_scriptures_js_gematria_lexicon_v1.py "
            "--scriptures-js-dir storage/external_kg/scriptures_js_v1 --ack-license-verify-upstream"
        ),
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "logos_scriptures_js_gematria_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "license_ack": license_ack,
        "scriptures_js_dir": _rel(src_dir),
        "stats": stats,
        "entries_built": len(rows),
        "out_jsonl": _rel(args.out_jsonl),
        "reproduce": manifest["reproduce"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(rows) >= args.min_entries
    print(json.dumps({"ok": ok, "entries_built": len(rows), "stats": stats}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
