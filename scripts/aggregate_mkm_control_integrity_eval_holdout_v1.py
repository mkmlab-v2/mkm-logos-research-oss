#!/usr/bin/env python3
"""Merge per-split control-integrity eval reports into one holdout suite report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = WORKSPACE_ROOT / "reports" / "mkm_control_integrity_lora_eval_holdout_suite_latest.json"


def _as_abs(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (WORKSPACE_ROOT / path)


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"expected object: {path}")
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate holdout eval reports (validation, test, locked_eval)")
    ap.add_argument(
        "--inputs",
        required=True,
        help="Comma-separated report JSON paths in order: validation,test,locked_eval",
    )
    ap.add_argument(
        "--profile-label",
        default="",
        help="Optional label (e.g. a_qwen25_base) for report metadata",
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output merged JSON path")
    args = ap.parse_args()

    paths = [_as_abs(x.strip()) for x in args.inputs.split(",") if x.strip()]
    if len(paths) != 3:
        print("expected exactly 3 report paths: validation,test,locked_eval")
        return 1

    split_names = ("validation", "test", "locked_eval")
    by_split: dict[str, Any] = {}
    errors: list[str] = []
    total_rows = 0
    weighted_row_pass = 0.0
    weighted_include = 0.0
    weighted_coverage = 0.0
    all_ok = True

    for sp, path in zip(split_names, paths):
        if not path.is_file():
            errors.append(f"missing: {path}")
            continue
        rep = _load(path)
        if not rep.get("ok", False):
            all_ok = False
        s = rep.get("summary", {})
        n = int(s.get("rows_total", 0))
        total_rows += n
        if n:
            weighted_row_pass += float(s.get("row_pass_rate", 0.0)) * n
            weighted_include += float(s.get("must_include_pass_rate", 0.0)) * n
            weighted_coverage += float(s.get("coverage_rate", 0.0)) * n
        by_split[sp] = {
            "report_path": str(path),
            "summary": s,
            "ok": rep.get("ok", False),
        }

    w_row = (weighted_row_pass / total_rows) if total_rows else 0.0
    w_inc = (weighted_include / total_rows) if total_rows else 0.0
    w_cov = (weighted_coverage / total_rows) if total_rows else 0.0

    out = _as_abs(args.out)
    result = {
        "schema": "mkm_control_integrity_lora_eval_holdout_suite_v1",
        "profile_label": args.profile_label or None,
        "splits": list(split_names),
        "by_split": by_split,
        "summary": {
            "rows_total": total_rows,
            "row_pass_rate_weighted": round(w_row, 4),
            "must_include_pass_rate_weighted": round(w_inc, 4),
            "coverage_rate_weighted": round(w_cov, 4),
        },
        "errors": errors,
        "ok": len(errors) == 0 and all_ok,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"rows_total={total_rows}")
    print(f"row_pass_rate_weighted={w_row:.4f}")
    print(f"errors={len(errors)}")
    print(f"out={out}")
    return 0 if len(errors) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
