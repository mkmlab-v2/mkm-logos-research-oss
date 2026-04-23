#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate canon-only singularity outputs (v1).")
    ap.add_argument(
        "--report-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_only_v1.json",
    )
    ap.add_argument(
        "--balanced-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_balanced_canon_only_v1.json",
    )
    ap.add_argument(
        "--summary-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_lane_summary_v1.json",
    )
    ap.add_argument("--expected-canon-rows", type=int, default=28741)
    ap.add_argument("--min-top-global", type=int, default=1)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_v1.json",
    )
    args = ap.parse_args()

    report = _read_json(Path(args.report_json))
    balanced = _read_json(Path(args.balanced_json))
    summary = _read_json(Path(args.summary_json))

    _require(bool(report.get("inputs", {}).get("canon_only")), "report.inputs.canon_only must be true")
    _require(report.get("counts", {}).get("dss_rows") == 0, "report.counts.dss_rows must be 0")
    _require(report.get("counts", {}).get("apocrypha_rows") == 0, "report.counts.apocrypha_rows must be 0")
    _require(
        int(report.get("counts", {}).get("canon_rows", -1)) == int(args.expected_canon_rows),
        f"report.counts.canon_rows must be {args.expected_canon_rows}",
    )
    top_global = report.get("top_global_singularities") or []
    _require(len(top_global) >= int(args.min_top_global), "report.top_global_singularities is empty")
    _require(all((r.get("lane") == "canon") for r in top_global), "report.top_global contains non-canon lane")

    _require(bool(balanced.get("inputs", {}).get("canon_only")), "balanced.inputs.canon_only must be true")
    _require(balanced.get("counts", {}).get("dss_rows") == 0, "balanced.counts.dss_rows must be 0")
    _require(balanced.get("counts", {}).get("apocrypha_rows") == 0, "balanced.counts.apocrypha_rows must be 0")
    _require(
        int(balanced.get("counts", {}).get("canon_rows", -1)) == int(args.expected_canon_rows),
        f"balanced.counts.canon_rows must be {args.expected_canon_rows}",
    )
    _require((balanced.get("balanced_union_top") or []), "balanced.balanced_union_top is empty")

    _require(
        summary.get("schema") == "original_corpus_regime_singularity_canon_lane_summary_v1",
        "summary.schema mismatch",
    )
    _require(summary.get("counts", {}).get("canon_rows_in_source_top", 0) > 0, "summary canon_rows_in_source_top must be > 0")
    _require((summary.get("top_canon_global") or []), "summary.top_canon_global is empty")

    out = {
        "schema": "original_corpus_regime_singularity_canon_quality_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result": "pass",
        "inputs": {
            "report_json": str(args.report_json),
            "balanced_json": str(args.balanced_json),
            "summary_json": str(args.summary_json),
            "expected_canon_rows": int(args.expected_canon_rows),
            "min_top_global": int(args.min_top_global),
        },
        "checks": {
            "report_canon_only": True,
            "report_no_dss": True,
            "report_no_apocrypha": True,
            "report_expected_rows": True,
            "report_top_global_nonempty": True,
            "report_top_global_canon_lane_only": True,
            "balanced_canon_only": True,
            "balanced_no_dss": True,
            "balanced_no_apocrypha": True,
            "balanced_expected_rows": True,
            "balanced_union_nonempty": True,
            "summary_schema_ok": True,
            "summary_counts_positive": True,
            "summary_top_global_nonempty": True,
        },
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: canon singularity outputs validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise

