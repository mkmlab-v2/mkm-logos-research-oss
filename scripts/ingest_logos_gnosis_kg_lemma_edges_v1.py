#!/usr/bin/env python3
"""Ingest Gnosis KG word-level Strong's rows into logos_lemma_verse_edges [HYPO].

Requires local Gnosis export directory (GitHub Releases JSON). No network fetch.
License gate: --ack-license-cc-by-sa-4 (Gnosis CC-BY-SA 4.0 — verify SOURCES.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_gnosis_kg_lemma_edges_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/logos_gnosis_kg_ingest_v1_latest.json"
DEFAULT_MERGE = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_MERGE_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
FIXTURE_DIR = ROOT / "tests/fixtures/gnosis_kg_sample_v1"

LICENSE_ACK = "CC-BY-SA-4.0"
EDGE_TYPE = "GNOSIS_STRONGS_CONTAIN"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_word_verses(doc: Any) -> Iterator[tuple[str, list[dict[str, Any]], str]]:
    """Yield (osis_ref, words, lang) from Gnosis hebrew/greek export shapes."""
    if isinstance(doc, list):
        for item in doc:
            if not isinstance(item, dict):
                continue
            osis = str(item.get("osis_ref") or item.get("ref") or "")
            words = item.get("words") or []
            lang = "hebrew" if "lemma_raw" in (words[0] if words else {}) else "greek"
            if osis and isinstance(words, list):
                yield osis, words, lang
        return
    if isinstance(doc, dict):
        for key, item in doc.items():
            if isinstance(item, dict) and item.get("words"):
                osis = str(item.get("osis_ref") or item.get("ref") or key)
                words = item.get("words") or []
                lang = "hebrew" if "lemma_raw" in (words[0] if words else {}) else "greek"
                yield osis, words, lang


def _lemma_src(lang: str, strongs: str, lemma: str) -> str:
    strongs_norm = strongs.strip().upper()
    lemma_slug = lemma.strip().replace(" ", "_")[:48] if lemma else ""
    if lemma_slug:
        return f"lemma:gnosis:{lang}:{strongs_norm}:{lemma_slug}"
    return f"lemma:gnosis:{lang}:{strongs_norm}"


def build_edges_from_gnosis_dir(
    gnosis_dir: Path,
    *,
    max_edges: int,
    max_words_per_verse: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats: dict[str, Any] = {
        "hebrew_verses": 0,
        "greek_verses": 0,
        "edges_built": 0,
        "skipped_no_strongs": 0,
        "skipped_bad_ref": 0,
    }
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    edge_i = 0

    lang_files = [
        ("hebrew-words.json", "hebrew"),
        ("greek-words.json", "greek"),
    ]
    for fname, lang in lang_files:
        path = gnosis_dir / fname
        if not path.is_file():
            continue
        doc = _load_json(path)
        for osis_ref, words, detected_lang in _iter_word_verses(doc):
            use_lang = lang if lang else detected_lang
            vid = canonical_verse_ref(osis_ref)
            if not vid:
                stats["skipped_bad_ref"] += 1
                continue
            if use_lang == "hebrew":
                stats["hebrew_verses"] += 1
            else:
                stats["greek_verses"] += 1
            for word in words[:max_words_per_verse]:
                if len(rows) >= max_edges:
                    break
                if not isinstance(word, dict):
                    continue
                strongs = str(word.get("strongs_number") or "").strip()
                if not strongs:
                    stats["skipped_no_strongs"] += 1
                    continue
                lemma = str(word.get("lemma_raw") or word.get("lemma") or word.get("text") or "")
                src = _lemma_src(use_lang, strongs, lemma)
                key = (src, vid, EDGE_TYPE)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "schema": "logos_lemma_verse_edge_v1",
                        "edge_id": f"lemma_verse::gnosis_{edge_i}",
                        "src_node_id": src,
                        "dst_node_id": vid,
                        "edge_type": EDGE_TYPE,
                        "weight": 0.85,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "source": "gnosis_kg",
                        "license": LICENSE_ACK,
                        "strongs_number": strongs.upper(),
                        "corpus_hint": use_lang,
                    }
                )
                edge_i += 1
                stats["edges_built"] += 1
            if len(rows) >= max_edges:
                break
        if len(rows) >= max_edges:
            break

    return rows, stats


def merge_jsonl(
    *,
    base_path: Path,
    new_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    existing: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    if base_path.is_file():
        for line in base_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (
                str(row.get("src_node_id")),
                str(row.get("dst_node_id")),
                str(row.get("edge_type")),
            )
            seen.add(key)
            existing.append(row)
    added = 0
    for row in new_rows:
        key = (
            str(row.get("src_node_id")),
            str(row.get("dst_node_id")),
            str(row.get("edge_type")),
        )
        if key in seen:
            continue
        seen.add(key)
        existing.append(row)
        added += 1
    return existing, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gnosis-dir", type=Path, default=None, help="Local Gnosis JSON export directory")
    ap.add_argument(
        "--use-fixture-sample",
        action="store_true",
        help="Use tests/fixtures/gnosis_kg_sample_v1 (offline pytest / smoke)",
    )
    ap.add_argument(
        "--ack-license-cc-by-sa-4",
        action="store_true",
        help="Required for non-fixture ingest (Gnosis CC-BY-SA 4.0)",
    )
    ap.add_argument("--max-edges", type=int, default=50000)
    ap.add_argument("--max-words-per-verse", type=int, default=12)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--merge-into", type=Path, default=DEFAULT_MERGE)
    ap.add_argument("--merge-manifest", type=Path, default=DEFAULT_MERGE_MANIFEST)
    ap.add_argument("--no-merge", action="store_true")
    ap.add_argument("--min-edges", type=int, default=3, help="Fail if fewer edges built (fixture smoke=3)")
    args = ap.parse_args()

    if args.use_fixture_sample:
        gnosis_dir = FIXTURE_DIR
    elif args.gnosis_dir:
        gnosis_dir = args.gnosis_dir
        if not args.ack_license_cc_by_sa_4:
            raise SystemExit("non-fixture ingest requires --ack-license-cc-by-sa-4")
    else:
        raise SystemExit("provide --gnosis-dir or --use-fixture-sample")

    if not gnosis_dir.is_dir():
        raise SystemExit(f"missing gnosis dir: {gnosis_dir}")

    rows, stats = build_edges_from_gnosis_dir(
        gnosis_dir,
        max_edges=args.max_edges,
        max_words_per_verse=args.max_words_per_verse,
    )

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    merged_added = 0
    merged_total = len(rows)
    if not args.no_merge and args.merge_into:
        merged, merged_added = merge_jsonl(base_path=args.merge_into, new_rows=rows)
        merged_total = len(merged)
        args.merge_into.parent.mkdir(parents=True, exist_ok=True)
        args.merge_into.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
            encoding="utf-8",
        )
        if args.merge_manifest:
            manifest = {
                "schema": "logos_lemma_verse_edges_v1",
                "generated_at_utc": _utc(),
                "hypothesis_tier": "B",
                "research_only": True,
                "edge_count": merged_total,
                "gnosis_kg_ingest_added": merged_added,
                "note": "Merged prior edges + Gnosis Strong's CONTAIN rows; morphology from upstream Gnosis.",
                "reproduce": "py scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py --gnosis-dir <dir> --ack-license-cc-by-sa-4",
            }
            args.merge_manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    report = {
        "schema": "logos_gnosis_kg_ingest_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "license_ack": LICENSE_ACK if not args.use_fixture_sample else "fixture_offline_only",
        "gnosis_dir": _rel(gnosis_dir),
        "stats": stats,
        "edges_built": len(rows),
        "merge_added": merged_added,
        "merge_total_edges": merged_total,
        "out_jsonl": _rel(args.out_jsonl),
        "reproduce": "py scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py --use-fixture-sample",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(rows) >= args.min_edges
    print(
        json.dumps(
            {"ok": ok, "edges_built": len(rows), "merge_added": merged_added, "stats": stats},
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
