#!/usr/bin/env python3
"""Extract symbol candidates from DSS/Apocrypha manuscript corpora."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DSS = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed.jsonl"
DEFAULT_DSS_ENRICHED = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
DEFAULT_APO = ROOT / "data" / "logos" / "manuscripts" / "apocrypha_std.jsonl"
DEFAULT_ALLOWLIST = ROOT / "data" / "logos" / "verse_decoded_v2.jsonl"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_summary_latest.json"

WORD_RE = re.compile(r"[A-Za-z]+|[0-9]+|[\u0370-\u03FF]+|[\u0590-\u05FF]+")
NUMERIC_SYMBOL_KEEP = {"7", "12", "40", "70", "144000"}

STOPWORDS_EN = {
    "the", "and", "of", "to", "in", "is", "with", "for", "that", "on", "as", "be",
    "are", "by", "from", "at", "or", "an", "a", "it", "this", "his", "her", "their",
    "who", "them", "he", "she", "you", "your", "we", "our", "was", "were", "not",
    "they", "him", "all", "will", "my", "unto", "had", "so", "when", "us", "shall",
    "thou", "thy", "then", "have", "said", "their", "there", "what", "which", "into",
    "been", "also", "than", "these", "those", "after", "before", "over", "under",
    "more", "most", "such", "only", "very", "can", "could", "should", "would",
    "may", "might", "must", "do", "does", "did", "done",
}

# Common Hebrew particles/pronouns that dominate frequency but are low-symbol value.
STOPWORDS_HE = {
    "את", "על", "אל", "כי", "לא", "הוא", "היא", "אני", "אנחנו", "אתם", "אתן",
    "הם", "הן", "זה", "זאת", "אשר", "גם", "אם", "עם", "מן", "מ", "ו", "ב", "ל",
}


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _extract_text(row: dict[str, Any]) -> str:
    for k in ("text", "text_hebrew", "text_greek"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _tokenize(text: str) -> list[str]:
    toks = [m.group(0).lower() for m in WORD_RE.finditer(text)]
    out: list[str] = []
    for t in toks:
        if t in NUMERIC_SYMBOL_KEEP:
            out.append(t)
            continue
        if len(t) < 2:
            continue
        if re.fullmatch(r"[a-z]+", t) and t in STOPWORDS_EN:
            continue
        if re.fullmatch(r"[\u0590-\u05FF]+", t) and t in STOPWORDS_HE:
            continue
        out.append(t)
    return out


def _ngrams(tokens: list[str]) -> list[str]:
    grams = list(tokens)
    for i in range(len(tokens) - 1):
        grams.append(f"{tokens[i]} {tokens[i+1]}")
    return grams


def _idf(total_docs: int, df: int) -> float:
    return math.log((1 + total_docs) / (1 + df)) + 1.0


def _load_allowlist_tokens(path: Path) -> set[str]:
    bag: set[str] = set()
    for row in _iter_jsonl(path):
        text = " ".join(
            str(row.get(k, "") or "") for k in ("text", "original_text", "text_hebrew", "text_greek")
        )
        for tok in _tokenize(text):
            bag.add(tok)
    return bag


def _is_allowlisted_symbol(symbol: str, allow: set[str]) -> bool:
    parts = symbol.split()
    if not parts:
        return False
    if len(parts) == 1:
        return parts[0] in allow
    return all(p in allow for p in parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract B-Track symbol candidates from manuscripts")
    ap.add_argument("--dss", default=str(DEFAULT_DSS))
    ap.add_argument("--apo", default=str(DEFAULT_APO))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    ap.add_argument(
        "--token-allowlist-jsonl",
        default=str(DEFAULT_ALLOWLIST),
        help="Verse JSONL token allowlist for vector-connectable symbol filtering",
    )
    ap.add_argument("--top-k", type=int, default=300)
    ap.add_argument("--min-df", type=int, default=2)
    ap.add_argument("--max-df-ratio", type=float, default=0.2, help="Drop symbols appearing in too many docs")
    args = ap.parse_args()

    dss_path = _abs(args.dss)
    apo_path = _abs(args.apo)
    allow_path = _abs(args.token_allowlist_jsonl)
    # Prefer enriched DSS corpus only when caller did not explicitly set --dss.
    dss_explicit = "--dss" in sys.argv
    if (not dss_explicit) and dss_path == DEFAULT_DSS and DEFAULT_DSS_ENRICHED.is_file():
        dss_path = DEFAULT_DSS_ENRICHED
    out_path = _abs(args.out)
    summary_path = _abs(args.summary)
    for p in (dss_path, apo_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2
    allow_tokens: set[str] = set()
    if allow_path.is_file():
        allow_tokens = _load_allowlist_tokens(allow_path)

    tf = Counter()
    df = Counter()
    corpora_counter = defaultdict(Counter)  # symbol -> corpus counts
    total_docs = 0

    for source_name, path in (("dss", dss_path), ("apocrypha", apo_path)):
        for row in _iter_jsonl(path):
            text = _extract_text(row)
            if not text:
                continue
            toks = _tokenize(text)
            grams = _ngrams(toks)
            if not grams:
                continue
            total_docs += 1
            unique = set(grams)
            for g in grams:
                tf[g] += 1
                corpora_counter[g][source_name] += 1
            for g in unique:
                df[g] += 1

    scored: list[tuple[str, float]] = []
    for sym, term_freq in tf.items():
        doc_freq = df[sym]
        if doc_freq < args.min_df:
            continue
        if total_docs > 0 and (doc_freq / total_docs) > args.max_df_ratio:
            continue
        score = float(term_freq) * _idf(total_docs, doc_freq)
        scored.append((sym, score))
    pre_allowlist_count = len(scored)
    if allow_tokens:
        scored = [(sym, sc) for sym, sc in scored if _is_allowlisted_symbol(sym, allow_tokens)]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: args.top_k]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for rank, (sym, score) in enumerate(top, 1):
        row = {
            "rank": rank,
            "symbol": sym,
            "score_tfidf_like": round(score, 6),
            "term_freq": int(tf[sym]),
            "doc_freq": int(df[sym]),
            "source_mix": {
                "dss": int(corpora_counter[sym]["dss"]),
                "apocrypha": int(corpora_counter[sym]["apocrypha"]),
            },
            "generated_at_utc": ts,
        }
        rows.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "schema": "btrack_symbol_candidates_v1",
        "generated_at_utc": ts,
        "inputs": {"dss": str(dss_path), "apocrypha": str(apo_path)},
        "stats": {
            "total_docs": total_docs,
            "unique_symbols_before_filter": len(tf),
            "unique_symbols_after_df_filter": pre_allowlist_count,
            "unique_symbols_after_filter": len(scored),
            "top_k": len(rows),
            "min_df": args.min_df,
            "allowlist_tokens": len(allow_tokens),
        },
        "top10_preview": rows[:10],
        "output_jsonl": str(out_path),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: symbol candidates extracted")
    print(f"out={out_path}")
    print(f"summary={summary_path}")
    print(f"top_k={len(rows)} total_docs={total_docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
