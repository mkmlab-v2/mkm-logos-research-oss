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


def _write_output(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


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
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_history_v1.jsonl",
    )
    args = ap.parse_args()

    out_path = Path(args.output_json)
    history_path = Path(args.history_jsonl)
    checks = {
        "report_canon_only": False,
        "report_no_dss": False,
        "report_no_apocrypha": False,
        "report_expected_rows": False,
        "report_top_global_nonempty": False,
        "report_top_global_canon_lane_only": False,
        "balanced_canon_only": False,
        "balanced_no_dss": False,
        "balanced_no_apocrypha": False,
        "balanced_expected_rows": False,
        "balanced_union_nonempty": False,
        "summary_schema_ok": False,
        "summary_counts_positive": False,
        "summary_top_global_nonempty": False,
    }
    base_out = {
        "schema": "original_corpus_regime_singularity_canon_quality_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "report_json": str(args.report_json),
            "balanced_json": str(args.balanced_json),
            "summary_json": str(args.summary_json),
            "expected_canon_rows": int(args.expected_canon_rows),
            "min_top_global": int(args.min_top_global),
        },
    }

    try:
        report = _read_json(Path(args.report_json))
        balanced = _read_json(Path(args.balanced_json))
        summary = _read_json(Path(args.summary_json))

        _require(bool(report.get("inputs", {}).get("canon_only")), "report.inputs.canon_only must be true")
        checks["report_canon_only"] = True
        _require(report.get("counts", {}).get("dss_rows") == 0, "report.counts.dss_rows must be 0")
        checks["report_no_dss"] = True
        _require(report.get("counts", {}).get("apocrypha_rows") == 0, "report.counts.apocrypha_rows must be 0")
        checks["report_no_apocrypha"] = True
        _require(
            int(report.get("counts", {}).get("canon_rows", -1)) == int(args.expected_canon_rows),
            f"report.counts.canon_rows must be {args.expected_canon_rows}",
        )
        checks["report_expected_rows"] = True
        top_global = report.get("top_global_singularities") or []
        _require(len(top_global) >= int(args.min_top_global), "report.top_global_singularities is empty")
        checks["report_top_global_nonempty"] = True
        _require(all((r.get("lane") == "canon") for r in top_global), "report.top_global contains non-canon lane")
        checks["report_top_global_canon_lane_only"] = True

        _require(bool(balanced.get("inputs", {}).get("canon_only")), "balanced.inputs.canon_only must be true")
        checks["balanced_canon_only"] = True
        _require(balanced.get("counts", {}).get("dss_rows") == 0, "balanced.counts.dss_rows must be 0")
        checks["balanced_no_dss"] = True
        _require(balanced.get("counts", {}).get("apocrypha_rows") == 0, "balanced.counts.apocrypha_rows must be 0")
        checks["balanced_no_apocrypha"] = True
        _require(
            int(balanced.get("counts", {}).get("canon_rows", -1)) == int(args.expected_canon_rows),
            f"balanced.counts.canon_rows must be {args.expected_canon_rows}",
        )
        checks["balanced_expected_rows"] = True
        _require((balanced.get("balanced_union_top") or []), "balanced.balanced_union_top is empty")
        checks["balanced_union_nonempty"] = True

        _require(
            summary.get("schema") == "original_corpus_regime_singularity_canon_lane_summary_v1",
            "summary.schema mismatch",
        )
        checks["summary_schema_ok"] = True
        _require(summary.get("counts", {}).get("canon_rows_in_source_top", 0) > 0, "summary canon_rows_in_source_top must be > 0")
        checks["summary_counts_positive"] = True
        _require((summary.get("top_canon_global") or []), "summary.top_canon_global is empty")
        checks["summary_top_global_nonempty"] = True

        _write_output(
            out_path,
            {
                **base_out,
                "result": "pass",
                "checks": checks,
            },
        )
        _append_jsonl(
            history_path,
            {
                "schema": "original_corpus_regime_singularity_canon_quality_gate_event_v1",
                "generated_at_utc": base_out["generated_at_utc"],
                "result": "pass",
                "error": None,
                "inputs": base_out["inputs"],
                "checks": checks,
            },
        )
        print("OK: canon singularity outputs validated")
        return 0
    except Exception as e:
        _write_output(
            out_path,
            {
                **base_out,
                "result": "fail",
                "error": str(e),
                "checks": checks,
            },
        )
        _append_jsonl(
            history_path,
            {
                "schema": "original_corpus_regime_singularity_canon_quality_gate_event_v1",
                "generated_at_utc": base_out["generated_at_utc"],
                "result": "fail",
                "error": str(e),
                "inputs": base_out["inputs"],
                "checks": checks,
            },
        )
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

