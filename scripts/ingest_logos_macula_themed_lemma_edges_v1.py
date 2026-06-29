#!/usr/bin/env python3
"""Track B MACULA-themed lemma↔verse ingest (MACULA TSV optional + distill/verse fallback)."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

THEME_PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
DEFAULT_OUT_JSONL = ROOT / "docs/final/artifacts/logos_macula_themed_lemma_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/logos_macula_themed_ingest_v1_latest.json"
DEFAULT_MERGE_TARGET = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_MERGE_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"

GREEK_RE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]{2,}")
HEBREW_RE = re.compile(r"[\u0590-\u05FF]{2,}")

BOOK_MACULA_TO_MKM: dict[str, str] = {
    "JHN": "Jhn",
    "JOH": "Jhn",
    "JOHN": "Jhn",
    "DAN": "Dan",
    "MAT": "Matt",
    "MRK": "Mark",
    "LUK": "Luke",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _theme_verse_ids(presets: dict[str, Any], theme_id: str) -> set[str]:
    themes = presets.get("themes") or {}
    theme = themes.get(theme_id) if isinstance(themes, dict) else None
    if not isinstance(theme, dict):
        return set()
    prefix = str(theme.get("verse_prefix") or "")
    distill_path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    distill = _load_json(distill_path)
    ids: set[str] = set()
    if distill:
        for ref in distill.get("evidence_refs") or []:
            if isinstance(ref, dict) and ref.get("verse_id"):
                vid = canonical_verse_ref(str(ref["verse_id"]))
                if vid and (not prefix or vid.startswith(prefix)):
                    ids.add(vid)
    return ids


def _tokens_from_text(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for tok in GREEK_RE.findall(text):
        out.append(("greek", tok))
    for tok in HEBREW_RE.findall(text):
        out.append(("hebrew", tok))
    return out


def _edges_from_distill(theme_id: str, verse_ids: set[str]) -> list[dict[str, Any]]:
    distill_path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    distill = _load_json(distill_path)
    if not distill:
        return []
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    edge_i = 0
    for ref in distill.get("evidence_refs") or []:
        if not isinstance(ref, dict):
            continue
        vid = canonical_verse_ref(str(ref.get("verse_id") or ""))
        if not vid or vid not in verse_ids:
            continue
        snippet = str(ref.get("hash_tagged_snippet") or "")
        for lang, tok in _tokens_from_text(snippet)[:12]:
            lemma_id = f"lemma:macula_proxy:{lang}:{tok}"
            key = (lemma_id, vid)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "schema": "logos_lemma_verse_edge_v1",
                    "edge_id": f"lemma_verse::macula_distill_{theme_id}_{edge_i}",
                    "src_node_id": lemma_id,
                    "dst_node_id": vid,
                    "edge_type": "MACULA_PROXY_DISTILL",
                    "weight": 0.55,
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "theme_id": theme_id,
                    "source": "logos_deep_research_distill_citation_lock",
                }
            )
            edge_i += 1
    return rows


def _iter_macula_tsv_rows(tsv_path: Path) -> Iterator[dict[str, str]]:
    with tsv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row:
                yield {k.strip(): (v or "").strip() for k, v in row.items()}


def _verse_from_macula_row(row: dict[str, str]) -> str:
    if row.get("ref"):
        return canonical_verse_ref(row["ref"])
    book = (row.get("book") or row.get("Book") or "").upper()
    ch = row.get("chapter") or row.get("ch") or row.get("Chapter") or ""
    vs = row.get("verse") or row.get("vs") or row.get("Verse") or ""
    mkm_book = BOOK_MACULA_TO_MKM.get(book, book.title() if book else "")
    if mkm_book and ch and vs:
        return canonical_verse_ref(f"{mkm_book}.{ch}.{vs}")
    return ""


def _edges_from_macula_tsv(
    tsv_path: Path,
    *,
    verse_ids: set[str],
    theme_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    edge_i = 0
    for row in _iter_macula_tsv_rows(tsv_path):
        vid = _verse_from_macula_row(row)
        if not vid or vid not in verse_ids:
            continue
        lemma = row.get("lemma") or row.get("Lemma") or row.get("word") or row.get("Word") or ""
        lang = "greek" if GREEK_RE.search(lemma) else "hebrew" if HEBREW_RE.search(lemma) else "other"
        if not lemma or lang == "other":
            continue
        lemma_id = f"lemma:macula:{lang}:{lemma}"
        key = (lemma_id, vid)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "schema": "logos_lemma_verse_edge_v1",
                "edge_id": f"lemma_verse::macula_tsv_{theme_id}_{edge_i}",
                "src_node_id": lemma_id,
                "dst_node_id": vid,
                "edge_type": "MACULA_CONTAIN",
                "weight": 0.75,
                "hypothesis_tier": "B",
                "research_only": True,
                "theme_id": theme_id,
                "source": tsv_path.name,
            }
        )
        edge_i += 1
    return rows


def _edges_from_verse_decoded(
    verse_jsonl: Path,
    *,
    verse_ids: set[str],
    theme_id: str,
    max_tokens_per_verse: int,
) -> list[dict[str, Any]]:
    if not verse_jsonl.is_file():
        return []
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    edge_i = 0
    with verse_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            vid = canonical_verse_ref(str(obj.get("verse_id") or ""))
            if vid not in verse_ids:
                continue
            corpus = ""
            text = str(obj.get("original_text") or obj.get("text") or "")
            if obj.get("greek_value"):
                corpus = "greek"
            elif obj.get("hebrew_value"):
                corpus = "hebrew"
            tokens = _tokens_from_text(text)[:max_tokens_per_verse]
            for lang, tok in tokens:
                lemma_id = f"lemma:verse_decoded:{lang}:{tok}"
                key = (lemma_id, vid)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "schema": "logos_lemma_verse_edge_v1",
                        "edge_id": f"lemma_verse::decoded_{theme_id}_{edge_i}",
                        "src_node_id": lemma_id,
                        "dst_node_id": vid,
                        "edge_type": "LEMMA_VERSE_DECODED",
                        "weight": 0.45,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "theme_id": theme_id,
                        "source": "verse_decoded_v2",
                        "corpus_hint": corpus or lang,
                    }
                )
                edge_i += 1
    return rows


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
    ap.add_argument("--themes", default="dan_aramaic,john_1_logos")
    ap.add_argument("--macula-tsv-dir", type=Path, default=None, help="Optional MACULA WLC/tsv directory")
    ap.add_argument("--verse-jsonl", type=Path, default=ROOT / "data/logos/verse_decoded_v2.jsonl")
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--merge-into", type=Path, default=DEFAULT_MERGE_TARGET)
    ap.add_argument("--merge-manifest", type=Path, default=DEFAULT_MERGE_MANIFEST)
    ap.add_argument("--max-tokens-per-verse", type=int, default=8)
    ap.add_argument("--no-merge", action="store_true")
    args = ap.parse_args()

    presets = _load_json(THEME_PRESETS)
    if not presets:
        raise SystemExit(f"missing presets: {THEME_PRESETS}")

    theme_ids = [t.strip() for t in args.themes.split(",") if t.strip()]
    all_new: list[dict[str, Any]] = []
    per_theme: dict[str, Any] = {}

    for theme_id in theme_ids:
        verse_ids = _theme_verse_ids(presets, theme_id)
        theme_rows: list[dict[str, Any]] = []
        theme_rows.extend(_edges_from_distill(theme_id, verse_ids))
        theme_rows.extend(
            _edges_from_verse_decoded(
                args.verse_jsonl,
                verse_ids=verse_ids,
                theme_id=theme_id,
                max_tokens_per_verse=args.max_tokens_per_verse,
            )
        )
        macula_count = 0
        if args.macula_tsv_dir and args.macula_tsv_dir.is_dir():
            for tsv in sorted(args.macula_tsv_dir.glob("*.tsv")):
                macula_rows = _edges_from_macula_tsv(tsv, verse_ids=verse_ids, theme_id=theme_id)
                macula_count += len(macula_rows)
                theme_rows.extend(macula_rows)
        all_new.extend(theme_rows)
        per_theme[theme_id] = {
            "verse_ids": len(verse_ids),
            "edges_built": len(theme_rows),
            "macula_tsv_edges": macula_count,
        }

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_new) + ("\n" if all_new else ""),
        encoding="utf-8",
    )

    merged_added = 0
    merged_total = len(all_new)
    if not args.no_merge and args.merge_into:
        merged, merged_added = merge_jsonl(base_path=args.merge_into, new_rows=all_new)
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
                "macula_themed_ingest_added": merged_added,
                "note": "Merged bridge/heuristic + MACULA-themed ingest; morphology MACULA when TSV provided.",
                "reproduce": "py scripts/ingest_logos_macula_themed_lemma_edges_v1.py",
            }
            args.merge_manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    doc = {
        "schema": "logos_macula_themed_ingest_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "themes": per_theme,
        "edges_built": len(all_new),
        "macula_tsv_dir": str(args.macula_tsv_dir) if args.macula_tsv_dir else None,
        "out_jsonl": str(args.out_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "merge_into": None if args.no_merge else str(args.merge_into.relative_to(ROOT)).replace("\\", "/"),
        "merge_added": merged_added,
        "merge_total_edges": merged_total,
        "reproduce": "py scripts/ingest_logos_macula_themed_lemma_edges_v1.py",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(all_new) >= 50
    print(json.dumps({"ok": ok, "edges_built": len(all_new), "merge_added": merged_added}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
