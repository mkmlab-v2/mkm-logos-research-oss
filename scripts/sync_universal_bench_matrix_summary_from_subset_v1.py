#!/usr/bin/env python3
"""Patch matrix summary headline from machine subset sweep artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBSET = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_290_subset_v1.json"
SUMMARY = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_summary_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset-json", type=Path, default=SUBSET)
    ap.add_argument("--summary-json", type=Path, default=SUMMARY)
    args = ap.parse_args()

    subset_path = (ROOT / args.subset_json).resolve() if not args.subset_json.is_absolute() else args.subset_json
    summary_path = (ROOT / args.summary_json).resolve() if not args.summary_json.is_absolute() else args.summary_json
    if not subset_path.is_file():
        print(json.dumps({"error": "missing_subset", "path": str(subset_path)}, ensure_ascii=False))
        return 2

    sub = json.loads(subset_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}

    headline = sub.get("headline") or {}
    summary["matrix_headline_290_excluding_chunk"] = {
        "economy_mean_saving_pct": headline.get("economy_mean_saving_pct"),
        "economy_mean_jaccard": headline.get("economy_mean_jaccard"),
        "case_count": sub.get("case_count"),
        "source": str(subset_path.relative_to(ROOT)).replace("\\", "/"),
        "excluded_lane_ids": sub.get("excluded_lane_ids")
        or ["ijeoma_chunk_table_v1", "ijeoma_chunk_cjk_hypo_v1"],
        "note": "290 operational KPI; excludes chunk_table (0% economy) and cjk_hypo (separate B-track bucket).",
    }
    summary.setdefault("artifacts", {})
    summary["artifacts"]["sweep_290_subset"] = str(subset_path.relative_to(ROOT)).replace("\\", "/")
    summary["artifacts"]["subset_script"] = "scripts/summarize_universal_bench_matrix_sweep_subset_v1.py"
    summary["artifacts"]["chunk_eval_debug"] = (
        "reports/constitution/btrack_pilot/comp_universal_bench_chunk_eval_debug_v1.json"
    )
    wire_subset = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_summary_290_subset_v1.json"
    if wire_subset.is_file():
        ws = json.loads(wire_subset.read_text(encoding="utf-8"))
        summary["wire_ab_290_subset"] = {
            "artifact": str(wire_subset.relative_to(ROOT)).replace("\\", "/"),
            "case_count": ws.get("case_count"),
            "weighted_headline": ws.get("weighted_headline"),
        }
    summary["summary_synced_at_utc"] = _utc()

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": summary_path.name, "headline_290": summary["matrix_headline_290_excluding_chunk"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
