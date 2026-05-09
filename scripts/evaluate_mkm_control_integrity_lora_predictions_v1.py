#!/usr/bin/env python3
"""Evaluate MKM control-integrity predictions against Golden Set v1.

Prediction file format (JSONL):
  {"id":"mkm-gs-v1-0001","prediction":"..."}

Default evaluation scope: split in {validation, test, locked_eval}
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLDEN = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_golden_set_v1_1000.jsonl"
DEFAULT_REPORT = WORKSPACE_ROOT / "reports" / "mkm_control_integrity_lora_eval_latest.json"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_no}: invalid json: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path} line {line_no}: row must be object")
            rows.append(obj)
    return rows


def _contains_all(text: str, patterns: list[str]) -> bool:
    t = _norm_text(text)
    return all(_norm_text(p) in t for p in patterns)


def _contains_any(text: str, patterns: list[str]) -> bool:
    t = _norm_text(text)
    return any(_norm_text(p) in t for p in patterns)


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate MKM control-integrity model predictions")
    ap.add_argument("--golden", default=str(DEFAULT_GOLDEN), help="Golden set JSONL path")
    ap.add_argument("--predictions", default="", help="Prediction JSONL path (id,prediction). Empty => oracle mode")
    ap.add_argument(
        "--splits",
        default="validation,test,locked_eval",
        help="Comma-separated split filter (default: validation,test,locked_eval)",
    )
    ap.add_argument("--report-out", default=str(DEFAULT_REPORT), help="Output report path")
    ap.add_argument(
        "--allow-missing-predictions",
        action="store_true",
        help="Do not treat missing ids as errors; score only rows with predictions (subset / --limit inference).",
    )
    args = ap.parse_args()

    golden_path = _as_abs(args.golden)
    report_out = _as_abs(args.report_out)
    if not golden_path.is_file():
        print(f"golden not found: {golden_path}")
        return 1

    split_filter = {s.strip() for s in args.splits.split(",") if s.strip()}
    golden_rows = _load_jsonl(golden_path)
    eval_rows = [r for r in golden_rows if str(r.get("split")) in split_filter]
    if not eval_rows:
        print(f"no rows for split filter: {sorted(split_filter)}")
        return 2

    predictions: dict[str, str] = {}
    mode = "oracle_expected_response"
    if args.predictions:
        pred_path = _as_abs(args.predictions)
        if not pred_path.is_file():
            print(f"predictions not found: {pred_path}")
            return 1
        mode = "model_predictions"
        for row in _load_jsonl(pred_path):
            rid = str(row.get("id", "")).strip()
            pred = str(row.get("prediction", ""))
            if rid:
                predictions[rid] = pred
    else:
        for r in eval_rows:
            predictions[str(r.get("sample_id", ""))] = str(r.get("expected_response", ""))

    total = len(eval_rows)
    found = 0
    exact_match = 0
    include_pass = 0
    exclude_pass = 0
    row_pass = 0
    by_split_total: Counter[str] = Counter()
    by_split_pass: Counter[str] = Counter()
    errors: list[str] = []

    sample_failures: list[dict[str, Any]] = []

    for row in eval_rows:
        sid = str(row.get("sample_id", ""))
        split = str(row.get("split", "unknown"))
        ref = str(row.get("expected_response", ""))
        pred = predictions.get(sid, "")

        if not pred:
            if args.allow_missing_predictions:
                continue
            errors.append(f"missing prediction: {sid}")
            continue

        found += 1
        by_split_total[split] += 1

        if _norm_text(pred) == _norm_text(ref):
            exact_match += 1

        must_include = [str(x) for x in row.get("must_include", []) if str(x).strip()]
        must_not = [str(x) for x in row.get("must_not_include", []) if str(x).strip()]
        include_ok = _contains_all(pred, must_include)
        exclude_ok = not _contains_any(pred, must_not)
        if include_ok:
            include_pass += 1
        if exclude_ok:
            exclude_pass += 1

        overall_ok = include_ok and exclude_ok and bool(pred.strip())
        if overall_ok:
            row_pass += 1
            by_split_pass[split] += 1
        elif len(sample_failures) < 20:
            sample_failures.append(
                {
                    "id": sid,
                    "split": split,
                    "include_ok": include_ok,
                    "exclude_ok": exclude_ok,
                    "must_include": must_include,
                    "must_not_include": must_not,
                }
            )

    coverage = found / total if total else 0.0
    denom = found if args.allow_missing_predictions else total
    exact_rate = exact_match / denom if denom else 0.0
    include_rate = include_pass / denom if denom else 0.0
    exclude_rate = exclude_pass / denom if denom else 0.0
    row_pass_rate = row_pass / denom if denom else 0.0

    report = {
        "schema": "mkm_control_integrity_lora_eval_report_v1",
        "mode": mode,
        "golden_path": str(golden_path),
        "prediction_path": args.predictions if args.predictions else None,
        "splits": sorted(split_filter),
        "summary": {
            "rows_total": total,
            "rows_with_prediction": found,
            "scored_rows_denominator": denom,
            "subset_scoring": bool(args.allow_missing_predictions and found and found < total),
            "coverage_rate": round(coverage, 4),
            "exact_match_rate": round(exact_rate, 4),
            "must_include_pass_rate": round(include_rate, 4),
            "must_not_include_pass_rate": round(exclude_rate, 4),
            "row_pass_rate": round(row_pass_rate, 4),
        },
        "by_split": {
            split: {
                "total": by_split_total.get(split, 0),
                "pass": by_split_pass.get(split, 0),
                "pass_rate": round(
                    (by_split_pass.get(split, 0) / by_split_total.get(split, 1))
                    if by_split_total.get(split, 0)
                    else 0.0,
                    4,
                ),
            }
            for split in sorted(by_split_total.keys())
        },
        "sample_failures": sample_failures,
        "errors": errors,
        "ok": len(errors) == 0,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    with report_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"rows={total}")
    print(f"coverage={coverage:.4f}")
    print(f"row_pass_rate={row_pass_rate:.4f}")
    print(f"errors={len(errors)}")
    print(f"report={report_out}")

    if mode == "model_predictions" and found == 0:
        print("no predictions matched golden scope; exit 1")
        return 1

    return 0 if len(errors) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
