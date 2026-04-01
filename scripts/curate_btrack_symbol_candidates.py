#!/usr/bin/env python3
"""Curate high-value symbol candidates from raw extraction output."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_latest.jsonl"
OUT_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_latest.jsonl"
OUT_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_summary_latest.json"

THEME_TERMS = {
    "lord", "god", "king", "israel", "wisdom", "light", "darkness", "covenant", "temple",
    "altar", "priest", "prophet", "judgment", "mercy", "truth", "peace", "righteous",
    "holy", "spirit", "word", "law", "kingdom", "battle", "war", "sons", "seed", "fire",
    "water", "bread", "life", "death", "sabbath", "jubilee",
    "יהוה", "אלהים", "אור", "חכמה", "ברית", "צדק", "שלום", "קדש", "משפט", "חסד",
}
NUMERIC_SYMBOL_THEMES = {"7", "12", "40", "70", "144000"}
NUMERIC_TEXT_THEMES = {
    "seven", "twelve", "forty", "seventy",
    "שבע", "שבעה", "שבעים", "שנים עשר", "שתים עשרה", "ארבעים",
}

DROP_TERMS = {
    "now", "upon", "but", "me", "thee", "up", "out", "one", "man", "day", "go", "br",
    "כִּי", "כי", "כל", "לֹא", "לא",
}

REQUIRED_PILOT_TERMS = {
    "god", "sons", "israel", "nations", "nation", "inheritance", "boundary", "tribes", "heaven", "divine",
    "אלהים", "בני", "ישראל", "עמים", "גוי", "נחלה", "גבול", "שבט", "שבטים", "שמים", "עליון",
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


def _is_theme_symbol(sym: str) -> bool:
    if sym in NUMERIC_SYMBOL_THEMES:
        return True
    if sym in NUMERIC_TEXT_THEMES:
        return True
    if sym in THEME_TERMS:
        return True
    if " " in sym:
        parts = sym.split()
        return any(
            (p in THEME_TERMS) or (p in NUMERIC_SYMBOL_THEMES) or (p in NUMERIC_TEXT_THEMES)
            for p in parts
        )
    return False


def _is_numeric_theme_symbol(sym: str) -> bool:
    if sym in NUMERIC_SYMBOL_THEMES or sym in NUMERIC_TEXT_THEMES:
        return True
    if " " in sym:
        parts = sym.split()
        return any((p in NUMERIC_SYMBOL_THEMES) or (p in NUMERIC_TEXT_THEMES) for p in parts)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Curate B-Track symbol candidates")
    ap.add_argument("--in-jsonl", default=str(IN_JSONL))
    ap.add_argument("--out-jsonl", default=str(OUT_JSONL))
    ap.add_argument("--out-summary", default=str(OUT_SUMMARY))
    ap.add_argument("--top-k", type=int, default=200)
    ap.add_argument(
        "--min-dss-quota",
        type=int,
        default=20,
        help="Minimum number of DSS-backed symbols to include when available.",
    )
    ap.add_argument(
        "--min-curated-count",
        type=int,
        default=20,
        help="Minimum curated rows. Backfill with required pilot terms when too small.",
    )
    args = ap.parse_args()

    in_path = _abs(args.in_jsonl)
    out_path = _abs(args.out_jsonl)
    summary_path = _abs(args.out_summary)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2

    curated: list[dict[str, Any]] = []
    dss_pool: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    for row in _iter_jsonl(in_path):
        input_rows.append(row)
        sym = str(row.get("symbol", "")).strip().lower()
        if not sym or sym in DROP_TERMS:
            continue
        source_mix = row.get("source_mix", {})
        dss_count = 0
        if isinstance(source_mix, dict):
            v = source_mix.get("dss", 0)
            if isinstance(v, (int, float)):
                dss_count = int(v)
        if dss_count > 0:
            dss_pool.append(row)
        if not _is_theme_symbol(sym):
            continue
        curated.append(row)

    # Soft-boost numeric symbols so low-frequency numeric expressions survive top-k truncation.
    curated.sort(
        key=lambda r: (
            1 if _is_numeric_theme_symbol(str(r.get("symbol", "")).strip().lower()) else 0,
            float(r.get("score_tfidf_like", 0.0) or 0.0),
        ),
        reverse=True,
    )
    # Preserve high-value theme symbols first, then enforce DSS quota to reduce source bias.
    curated = curated[: args.top_k]
    curated_keys = {str(r.get("symbol", "")).strip().lower() for r in curated}
    curated_dss_count = 0
    for r in curated:
        mix = r.get("source_mix", {})
        if isinstance(mix, dict) and isinstance(mix.get("dss"), (int, float)) and int(mix.get("dss")) > 0:
            curated_dss_count += 1

    if curated_dss_count < args.min_dss_quota:
        needed = args.min_dss_quota - curated_dss_count
        dss_pool = sorted(
            dss_pool,
            key=lambda r: (
                int(r.get("source_mix", {}).get("dss", 0)) if isinstance(r.get("source_mix"), dict) else 0,
                float(r.get("score_tfidf_like", 0.0) or 0.0),
            ),
            reverse=True,
        )
        for row in dss_pool:
            sym = str(row.get("symbol", "")).strip().lower()
            if not sym or sym in curated_keys:
                continue
            curated.append(row)
            curated_keys.add(sym)
            needed -= 1
            if needed <= 0:
                break

    if len(curated) < args.min_curated_count:
        candidates = []
        for row in input_rows:
            sym = str(row.get("symbol", "")).strip().lower()
            if sym in REQUIRED_PILOT_TERMS:
                candidates.append(row)
        candidates.sort(key=lambda r: float(r.get("score_tfidf_like", 0.0) or 0.0), reverse=True)
        for row in candidates:
            sym = str(row.get("symbol", "")).strip().lower()
            if not sym or sym in curated_keys:
                continue
            curated.append(row)
            curated_keys.add(sym)
            if len(curated) >= args.min_curated_count:
                break

    if len(curated) < args.min_curated_count:
        # Final fallback: fill from highest-score remaining symbols to guarantee minimal sample size.
        def _fallback_key(r: dict[str, Any]) -> tuple[int, float]:
            mix = r.get("source_mix", {})
            dss = 0
            if isinstance(mix, dict) and isinstance(mix.get("dss"), (int, float)):
                dss = int(mix.get("dss", 0))
            score = float(r.get("score_tfidf_like", 0.0) or 0.0)
            return (dss, score)

        fallback = sorted(input_rows, key=_fallback_key, reverse=True)
        for row in fallback:
            sym = str(row.get("symbol", "")).strip().lower()
            if not sym or sym in curated_keys or sym in DROP_TERMS:
                continue
            curated.append(row)
            curated_keys.add(sym)
            if len(curated) >= args.min_curated_count:
                break
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(curated, 1):
            row = dict(r)
            row["curated_rank"] = i
            row["curated_at_utc"] = ts
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "schema": "btrack_symbol_candidates_curated_v1",
        "generated_at_utc": ts,
        "input_jsonl": str(in_path),
        "output_jsonl": str(out_path),
        "curated_count": len(curated),
        "dss_backed_count": sum(
            1
            for r in curated
            if isinstance(r.get("source_mix"), dict)
            and isinstance(r.get("source_mix", {}).get("dss"), (int, float))
            and int(r.get("source_mix", {}).get("dss", 0)) > 0
        ),
        "min_dss_quota": args.min_dss_quota,
        "min_curated_count": args.min_curated_count,
        "top10_preview": curated[:10],
        "note": "Theme-term curation with DSS quota to reduce corpus-source bias.",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: curated symbol candidates written")
    print(f"out={out_path}")
    print(f"summary={summary_path}")
    print(f"curated_count={len(curated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
