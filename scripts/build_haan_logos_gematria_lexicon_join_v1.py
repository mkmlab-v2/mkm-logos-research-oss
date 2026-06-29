#!/usr/bin/env python3
"""HAAN Logos Tier0 ↔ scriptures-js gematria lexicon join (skeleton v1).

Two-layer join: traditional mispar/isopsephy [FACT layer] + gematria_bridge_v1 vector_4d [HYPO ops].
research_only · send_gate HOLD · no Track A merge
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_scriptures_js_gematria_lib_v1 import normalize_strongs  # noqa: E402

RAW = ROOT / "docs/research/raw"
DEFAULT_LEXICON = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/haan_logos_gematria_lexicon_join_v1_latest.json"

GEMATRIA_TIER0_GLOBS = (
    "logos_성경에_나타난_숫자*_PAPER_DIGEST_tier0_v1.md",
    "logos_성서게마트리아_PAPER_DIGEST_tier0_v1.md",
)

# Paper-cited biblical number anchors (Tier0 text match → lexicon lookup).
NUMBER_ANCHORS: list[dict[str, Any]] = [
    {
        "id": "fish_153",
        "number": 153,
        "verse_hint": "Jn.21.11",
        "join_mode": "narrative_count",
        "reverse_lexicon_optional": True,
        "note": "Fish count — not a single-lemma gematria sum; optional reverse lexicon (isopsephy/mispar = 153)",
    },
    {
        "id": "beast_666",
        "number": 666,
        "verse_hint": "Rev.13.18",
        "strongs_seed": ["G5516"],
        "join_mode": "greek_isopsephy",
        "note": "χξϛ — traditional isopsephy 666",
    },
    {
        "id": "genealogy_14",
        "number": 14,
        "verse_hint": "Mt.1",
        "join_mode": "structural_count",
        "reverse_lexicon_optional": True,
        "note": "14×3 genealogy structure — optional mispar/isopsephy = 14 hits (not lemma sum)",
    },
    {
        "id": "thousand_1000",
        "number": 1000,
        "verse_hint": None,
        "join_mode": "usage_scope",
        "note": "Paper scope anchor only",
    },
]

_STRONGS_INLINE_RE = re.compile(r"\b([HG])\s*0*(\d{1,5})\b", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_number_mentions(text: str) -> list[int]:
    found: set[int] = set()
    if "153" in text:
        found.add(153)
    if "666" in text:
        found.add(666)
    if re.search(r"1,000|1000", text):
        found.add(1000)
    if re.search(r"14\s*대|14\s*×|14×", text):
        found.add(14)
    return sorted(found)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _compact_lexicon_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "strongs": row.get("strongs"),
        "lemma": row.get("lemma"),
        "gloss": row.get("gloss"),
        "language": row.get("language"),
        "gematria_traditional": row.get("gematria"),
        "vector_4d": row.get("vector_4d"),
        "kernel_recipe_id": row.get("kernel_recipe_id"),
        "lexicon_source": row.get("lexicon_source"),
    }


def load_lexicon_index(path: Path) -> tuple[dict[str, dict[str, Any]], dict[int, list[str]], dict[int, list[str]]]:
    by_strongs: dict[str, dict[str, Any]] = {}
    by_hebrew_hechrachi: dict[int, list[str]] = defaultdict(list)
    by_greek_standard: dict[int, list[str]] = defaultdict(list)

    with path.open(encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            row = json.loads(s)
            strongs = normalize_strongs(str(row.get("strongs") or ""))
            if not strongs:
                continue
            prev = by_strongs.get(strongs)
            if prev is None or str(row.get("lexicon_source") or "").endswith("tbesh") or str(
                row.get("lexicon_source") or ""
            ).endswith("tbesg"):
                by_strongs[strongs] = row
            gem = row.get("gematria") or {}
            if isinstance(gem, dict):
                if "mispar_hechrachi" in gem:
                    v = int(gem["mispar_hechrachi"])
                    if strongs not in by_hebrew_hechrachi[v]:
                        by_hebrew_hechrachi[v].append(strongs)
                if "isopsephy_standard" in gem:
                    v = int(gem["isopsephy_standard"])
                    if strongs not in by_greek_standard[v]:
                        by_greek_standard[v].append(strongs)
    return by_strongs, by_hebrew_hechrachi, by_greek_standard


def discover_gematria_tier0() -> list[Path]:
    found: list[Path] = []
    for pattern in GEMATRIA_TIER0_GLOBS:
        found.extend(sorted(RAW.glob(pattern)))
    # stable dedupe
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        key = _rel(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def extract_strongs_from_text(text: str) -> list[str]:
    hits: list[str] = []
    for m in _STRONGS_INLINE_RE.finditer(text):
        norm = normalize_strongs(f"{m.group(1)}{m.group(2)}")
        if norm and norm not in hits:
            hits.append(norm)
    return hits


def _reverse_hits_for_number(
    n: int,
    *,
    by_strongs: dict[str, dict[str, Any]],
    by_hebrew_hechrachi: dict[int, list[str]],
    by_greek_standard: dict[int, list[str]],
    reverse_cap: int,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sid in by_greek_standard.get(n, []) + by_hebrew_hechrachi.get(n, []):
        if sid in seen or sid not in by_strongs:
            continue
        seen.add(sid)
        hits.append(_compact_lexicon_entry(by_strongs[sid]))
        if len(hits) >= reverse_cap:
            break
    return hits


def join_anchor(
    anchor: dict[str, Any],
    *,
    mentioned: bool,
    by_strongs: dict[str, dict[str, Any]],
    by_hebrew_hechrachi: dict[int, list[str]],
    by_greek_standard: dict[int, list[str]],
    reverse_cap: int,
) -> dict[str, Any]:
    n = int(anchor["number"])
    row: dict[str, Any] = {
        "anchor_id": anchor["id"],
        "number": n,
        "verse_hint": anchor.get("verse_hint"),
        "join_mode": anchor.get("join_mode"),
        "mentioned_in_tier0": mentioned,
        "note": anchor.get("note"),
        "strongs_hits": [],
        "reverse_lexicon_hits": [],
    }
    if not mentioned:
        return row

    for sid in anchor.get("strongs_seed") or []:
        norm = normalize_strongs(str(sid))
        if norm and norm in by_strongs:
            row["strongs_hits"].append(_compact_lexicon_entry(by_strongs[norm]))

    for sid in anchor.get("strongs_seed") or []:
        continue
    if anchor.get("reverse_lexicon_optional"):
        row["reverse_lexicon_hits"] = _reverse_hits_for_number(
            n,
            by_strongs=by_strongs,
            by_hebrew_hechrachi=by_hebrew_hechrachi,
            by_greek_standard=by_greek_standard,
            reverse_cap=reverse_cap,
        )
    elif anchor.get("join_mode") == "greek_isopsephy":
        for sid in by_greek_standard.get(n, [])[:reverse_cap]:
            if sid in by_strongs:
                row["reverse_lexicon_hits"].append(_compact_lexicon_entry(by_strongs[sid]))
    elif anchor.get("join_mode") not in ("narrative_count", "structural_count", "usage_scope"):
        for sid in by_hebrew_hechrachi.get(n, [])[:reverse_cap]:
            if sid in by_strongs:
                row["reverse_lexicon_hits"].append(_compact_lexicon_entry(by_strongs[sid]))
    return row


def build_join(
    *,
    lexicon_path: Path,
    tier0_paths: list[Path],
    reverse_cap: int = 5,
) -> dict[str, Any]:
    by_strongs, by_hebrew, by_greek = load_lexicon_index(lexicon_path)
    papers: list[dict[str, Any]] = []

    for tier0 in tier0_paths:
        text = tier0.read_text(encoding="utf-8", errors="replace")
        inline_strongs = extract_strongs_from_text(text)
        numbers = extract_number_mentions(text)
        strongs_joins = [
            _compact_lexicon_entry(by_strongs[s]) for s in inline_strongs if s in by_strongs
        ]
        anchor_joins = [
            join_anchor(
                a,
                mentioned=a["number"] in numbers,
                by_strongs=by_strongs,
                by_hebrew_hechrachi=by_hebrew,
                by_greek_standard=by_greek,
                reverse_cap=reverse_cap,
            )
            for a in NUMBER_ANCHORS
        ]
        papers.append(
            {
                "tier0": _rel(tier0),
                "numbers_mentioned": numbers,
                "inline_strongs_extracted": inline_strongs,
                "strongs_joins": strongs_joins,
                "number_anchor_joins": anchor_joins,
            }
        )

    return {
        "schema": "haan_logos_gematria_lexicon_join_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "layer_contract": {
            "traditional": "gematria.mispar_* / isopsephy_* from scriptures-js lexicon — scholarly reference",
            "operational_4d": "vector_4d via gematria_bridge_v1 — B-track lookup only [HYPO]",
            "forbidden": "Track A promotion · prophecy claims · replacing verse subgraph SSOT",
        },
        "lexicon_path": _rel(lexicon_path),
        "lexicon_strongs_count": len(by_strongs),
        "papers": papers,
        "reproduce": "py scripts/build_haan_logos_gematria_lexicon_join_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reverse-cap", type=int, default=5)
    args = ap.parse_args()

    if not args.lexicon.is_file():
        print(json.dumps({"ok": False, "error": f"missing lexicon: {args.lexicon}"}, ensure_ascii=False))
        return 2

    tier0_paths = discover_gematria_tier0()
    if not tier0_paths:
        print(json.dumps({"ok": False, "error": "no gematria tier0 files"}, ensure_ascii=False))
        return 2

    doc = build_join(lexicon_path=args.lexicon, tier0_paths=tier0_paths, reverse_cap=args.reverse_cap)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    beast_hits = 0
    for p in doc["papers"]:
        for a in p.get("number_anchor_joins") or []:
            if a.get("anchor_id") == "beast_666" and a.get("strongs_hits"):
                beast_hits += 1

    print(
        json.dumps(
            {
                "ok": True,
                "papers": len(doc["papers"]),
                "lexicon_strongs": doc["lexicon_strongs_count"],
                "beast_666_strongs_joined": beast_hits,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
