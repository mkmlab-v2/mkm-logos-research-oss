#!/usr/bin/env python3
"""Summarize false negatives/positives from Layer-5 benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDSET = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_v1_latest.jsonl"
DEFAULT_BENCH = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_failure_report_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goldset-jsonl", type=Path, default=DEFAULT_GOLDSET)
    ap.add_argument("--benchmark-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cases", type=int, default=20)
    args = ap.parse_args()

    bench = _read_json(args.benchmark_json)
    goldset = _read_jsonl(args.goldset_jsonl)
    preview = bench.get("sample_preview") if isinstance(bench.get("sample_preview"), list) else []

    case_map = {str(row.get("case_id")): row for row in goldset if isinstance(row.get("case_id"), str)}
    fn_cases: list[dict[str, Any]] = []
    fp_cases: list[dict[str, Any]] = []
    fn_reason_counter: Counter[str] = Counter()

    for item in preview:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("case_id") or "")
        pred = bool(item.get("predicted_block"))
        exp = item.get("expected_block")
        source = case_map.get(cid, {})
        expected_reasons = source.get("expected_reasons")
        reasons = expected_reasons if isinstance(expected_reasons, list) else []
        for r in reasons:
            fn_reason_counter[str(r)] += 1

        row = {
            "case_id": cid,
            "predicted_block": pred,
            "expected_block": exp,
            "predicted_reasons": item.get("reasons") if isinstance(item.get("reasons"), list) else [],
            "expected_reasons": reasons,
            "source_file": source.get("source_file"),
            "source_line": source.get("source_line"),
        }
        if exp is True and pred is False:
            fn_cases.append(row)
        if exp is False and pred is True:
            fp_cases.append(row)

    out = {
        "schema": "layer5_policy_gate_failure_report_v1",
        "inputs": {
            "goldset_jsonl": str(args.goldset_jsonl).replace("\\", "/"),
            "benchmark_json": str(args.benchmark_json).replace("\\", "/"),
        },
        "benchmark_status": bench.get("benchmark_status"),
        "metrics": bench.get("metrics"),
        "false_negative_count_in_preview": len(fn_cases),
        "false_positive_count_in_preview": len(fp_cases),
        "top_expected_reason_tokens": [{"token": k, "count": v} for k, v in fn_reason_counter.most_common(20)],
        "false_negative_cases_preview": fn_cases[: max(0, args.max_cases)],
        "false_positive_cases_preview": fp_cases[: max(0, args.max_cases)],
        "note": "Analysis scope is benchmark sample_preview only.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "fn": len(fn_cases), "fp": len(fp_cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
