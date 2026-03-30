#!/usr/bin/env python3
"""Build DSS-only / Apocrypha-only / Mixed symbol split report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_latest.jsonl"
OUT_JSON = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_source_split_latest.json"


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


def _bucket(dss: float, apo: float) -> str:
    if dss > 0 and apo > 0:
        return "mixed"
    if dss > 0 and apo <= 0:
        return "dss_only"
    if apo > 0 and dss <= 0:
        return "apocrypha_only"
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Report curated symbol source split")
    ap.add_argument("--in-jsonl", default=str(IN_JSONL))
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--top-k-preview", type=int, default=20)
    args = ap.parse_args()

    in_path = _abs(args.in_jsonl)
    out_path = _abs(args.out_json)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2

    rows: list[dict[str, Any]] = []
    for row in _iter_jsonl(in_path):
        mix = row.get("source_mix", {})
        if not isinstance(mix, dict):
            mix = {}
        dss = float(mix.get("dss", 0.0) or 0.0)
        apo = float(mix.get("apocrypha", 0.0) or 0.0)
        b = _bucket(dss, apo)
        rows.append(
            {
                "symbol": row.get("symbol"),
                "score_tfidf_like": float(row.get("score_tfidf_like", 0.0) or 0.0),
                "term_freq": int(row.get("term_freq", 0) or 0),
                "doc_freq": int(row.get("doc_freq", 0) or 0),
                "source_mix": {"dss": int(dss), "apocrypha": int(apo)},
                "bucket": b,
            }
        )

    counts = {"dss_only": 0, "apocrypha_only": 0, "mixed": 0, "unknown": 0}
    scores = {"dss_only": 0.0, "apocrypha_only": 0.0, "mixed": 0.0, "unknown": 0.0}
    top: dict[str, list[dict[str, Any]]] = {k: [] for k in counts}
    for r in rows:
        b = str(r["bucket"])
        counts[b] += 1
        scores[b] += float(r["score_tfidf_like"])
        top[b].append(r)

    for k in top:
        top[k].sort(key=lambda x: float(x["score_tfidf_like"]), reverse=True)
        top[k] = top[k][: args.top_k_preview]

    total = len(rows)
    report = {
        "schema": "btrack_symbol_source_split_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_jsonl": str(in_path),
        "summary": {
            "total_curated_symbols": total,
            "counts": counts,
            "ratios": {k: round((v / total), 6) if total > 0 else 0.0 for k, v in counts.items()},
            "score_mass": {k: round(v, 6) for k, v in scores.items()},
        },
        "top_preview_by_bucket": top,
        "warning": (
            "If dss_only and mixed counts remain near zero, extraction is source-imbalanced. "
            "Increase DSS corpus rows before promotion decisions."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol source split report generated")
    print(f"out={out_path}")
    print(f"counts={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
