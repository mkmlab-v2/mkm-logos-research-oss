#!/usr/bin/env python3
"""Derive Deut 32:8 DSS lexical overlay from enriched DSS corpus."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_DSS_ENRICHED = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "dss_variant_lexicon_deut32_8_auto_latest.json"


TOKEN_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "god": (re.compile(r"\bgod\b", re.I), re.compile(r"אלהים"), re.compile(r"\belohim\b", re.I)),
    "sons": (re.compile(r"\bsons?\b", re.I), re.compile(r"בני")),
    "israel": (re.compile(r"\bisrael\b", re.I), re.compile(r"ישראל")),
    "nations": (re.compile(r"\bnations?\b", re.I), re.compile(r"גוים|עמים")),
    "inheritance": (re.compile(r"\binheritance\b", re.I), re.compile(r"נחלה")),
    "boundary": (re.compile(r"\bboundar(y|ies)\b", re.I), re.compile(r"גבול")),
    "divine": (re.compile(r"\bdivine\b", re.I), re.compile(r"עליון")),
    "nation": (re.compile(r"\bnation\b", re.I), re.compile(r"גוי")),
    "tribes": (re.compile(r"\btribes?\b", re.I), re.compile(r"שבט|שבטים")),
    "heaven": (re.compile(r"\bheaven\b", re.I), re.compile(r"שמים")),
}


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Deut 32:8 DSS lexical overlay from enriched corpus")
    ap.add_argument("--in-dss", default=str(IN_DSS_ENRICHED))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument(
        "--min-source-doc-support",
        type=int,
        default=2,
        help="Minimum unique source_doc support required per token.",
    )
    args = ap.parse_args()

    in_path = Path(args.in_dss)
    out_path = Path(args.out)
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    if not in_path.is_file():
        print(f"ERROR: missing file: {in_path}")
        return 2

    docs: list[dict[str, Any]] = list(_iter_jsonl(in_path))
    total_docs = len(docs)
    if total_docs == 0:
        print(f"ERROR: empty corpus: {in_path}")
        return 2

    df = Counter()
    token_docs: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, str] = {}
    for row in docs:
        text = str(row.get("text", "") or "")
        source_doc = str(row.get("source_doc", "") or "")
        seen_this_doc: set[str] = set()
        for token, patterns in TOKEN_PATTERNS.items():
            if any(p.search(text) for p in patterns):
                seen_this_doc.add(token)
                if token not in examples:
                    examples[token] = source_doc
        for token in seen_this_doc:
            source_key = source_doc or str(row.get("id", ""))
            token_docs[token].add(source_key)
            df[token] = len(token_docs[token])

    term_map: dict[str, dict[str, Any]] = {}
    for token in TOKEN_PATTERNS:
        support = df[token]
        if support < int(args.min_source_doc_support):
            continue
        weight = round(support / total_docs, 6)
        if weight <= 0:
            continue
        term_map[token] = {
            "dss_weight": weight,
            "doc_support": int(support),
            "doc_total": int(total_docs),
            "example_source_doc": examples.get(token),
            "method": "dss_enriched_unique_source_doc_frequency",
        }

    payload = {
        "schema": "dss_variant_lexicon_deut32_8_auto_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "Deut.32:8",
        "input_dss_enriched": str(in_path),
        "term_map": term_map,
        "stats": {
            "total_docs": total_docs,
            "tokens_with_support": len(term_map),
            "min_source_doc_support": int(args.min_source_doc_support),
        },
        "boundaries": {
            "fact": ["Token weights are derived from observed enriched DSS snippets."],
            "hypothesis": ["Coverage depends on current enriched snippet set and may be sparse."],
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: auto DSS lexicon generated")
    print(f"out={out_path}")
    print(f"tokens_with_support={len(term_map)} total_docs={total_docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
