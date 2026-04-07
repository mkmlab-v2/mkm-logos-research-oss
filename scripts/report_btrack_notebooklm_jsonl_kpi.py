#!/usr/bin/env python3
"""
Aggregate B-track NotebookLM mega-insight JSONL into observation-only KPIs.

Not predictive: evidence density, tag distribution, guardrail-style keyword rates.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports" / "notebooklm" / "btrack_mega_insights_10gb.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "btrack_notebooklm_jsonl_kpi_latest.json"

SCHEMA = "btrack_notebooklm_jsonl_kpi_v1"

GUARDRAIL_TOKENS = (
    "[HYPO]",
    "[NON-DETERMINISTIC]",
    "[NON-MEDICAL]",
    "OBSERVATION_ONLY",
    "B-Track",
    "A-Track",
)


def _percentile(sorted_vals: list[float | int], p: float) -> float | None:
    if not sorted_vals:
        return None
    xs = sorted(sorted_vals)
    n = len(xs)
    if n == 1:
        return float(xs[0])
    idx = (n - 1) * (p / 100.0)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return float(xs[lo] + frac * (xs[hi] - xs[lo]))


def _safe_len(obj: Any) -> int:
    if obj is None:
        return 0
    if isinstance(obj, (list, tuple)):
        return len(obj)
    if isinstance(obj, dict):
        return len(obj)
    return 0


def _process_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("schema") != "btrack_notebooklm_mega_insight_row_v1":
        return None
    ans = row.get("answer")
    if not isinstance(ans, str):
        return None
    n_src = _safe_len(row.get("sources_used"))
    cit = row.get("citations")
    n_cit = _safe_len(cit) if isinstance(cit, dict) else 0
    n_ref = _safe_len(row.get("references"))
    answer_len = len(ans)
    tags = row.get("tags")
    tag_list: list[str] = []
    if isinstance(tags, list):
        for t in tags:
            if isinstance(t, str) and t.strip():
                tag_list.append(t.strip())
    hits = {tok: (tok in ans) for tok in GUARDRAIL_TOKENS}
    return {
        "n_sources": n_src,
        "n_citations": n_cit,
        "n_references": n_ref,
        "answer_len": answer_len,
        "tags": tag_list,
        "guardrail_hits": hits,
    }


def run_kpi(input_path: Path) -> dict[str, Any]:
    rows_ok = 0
    rows_skipped = 0
    n_sources: list[int] = []
    n_citations: list[int] = []
    n_references: list[int] = []
    answer_lens: list[int] = []
    tag_counter: Counter[str] = Counter()
    guardrail_counts: Counter[str] = Counter()
    notebook_ids: Counter[str] = Counter()

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                rows_skipped += 1
                continue
            if not isinstance(row, dict):
                rows_skipped += 1
                continue
            m = _process_row(row)
            if m is None:
                rows_skipped += 1
                continue
            rows_ok += 1
            n_sources.append(m["n_sources"])
            n_citations.append(m["n_citations"])
            n_references.append(m["n_references"])
            answer_lens.append(m["answer_len"])
            for t in m["tags"]:
                tag_counter[t] += 1
            for tok, hit in m["guardrail_hits"].items():
                if hit:
                    guardrail_counts[tok] += 1
            nid = row.get("notebook_id")
            if isinstance(nid, str) and nid:
                notebook_ids[nid] += 1

    def dist_stats(vals: list[int]) -> dict[str, Any]:
        if not vals:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "p90": None,
            }
        return {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": round(statistics.mean(vals), 4),
            "median": float(statistics.median(vals)),
            "p90": _percentile(vals, 90.0),
        }

    guardrail_rates: dict[str, float | None] = {}
    for tok in GUARDRAIL_TOKENS:
        if rows_ok == 0:
            guardrail_rates[tok] = None
        else:
            guardrail_rates[tok] = round(guardrail_counts[tok] / rows_ok, 6)

    top_tags = [{"tag": t, "count": c} for t, c in tag_counter.most_common(50)]

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path.as_posix()),
        "disclaimer": (
            "B-track observation metrics only; not market prediction, A-track promotion, or TOE."
        ),
        "rows_total_valid": rows_ok,
        "rows_skipped": rows_skipped,
        "notebook_id_counts": dict(notebook_ids.most_common(20)),
        "distributions": {
            "n_sources_used": dist_stats(n_sources),
            "n_citations": dist_stats(n_citations),
            "n_references": dist_stats(n_references),
            "answer_char_len": dist_stats(answer_lens),
        },
        "guardrail_keyword_rates": guardrail_rates,
        "tag_counts_top": top_tags,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Report B-track NotebookLM JSONL KPIs.")
    ap.add_argument(
        "--input-jsonl",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input JSONL (default: {DEFAULT_INPUT})",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON (default: {DEFAULT_OUTPUT})",
    )
    args = ap.parse_args()
    if not args.input_jsonl.is_file():
        print(f"ERROR: input not found: {args.input_jsonl}", file=sys.stderr)
        return 2
    out = run_kpi(args.input_jsonl)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output_json} (rows_ok={out['rows_total_valid']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
