# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.82, K:0.36, M:0.44}
# Balance: 88
# Purpose: Validate real clinical evaluation input files before running evaluator.
# Keywords: sasang, validation, cohort, predictions, schema
#!/usr/bin/env python3
"""Validate GT cohort and prediction JSONL input schemas for sasang clinical eval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENTS = {"TY", "SY", "TE", "SE"}


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", default="data/constitution/korean_cohort/gt_cohort.real.latest.jsonl")
    ap.add_argument("--pred", default="reports/constitution/btrack_pilot/predictions.real.latest.jsonl")
    args = ap.parse_args()

    gt_path = _abs(args.gt)
    pred_path = _abs(args.pred)

    if not gt_path.is_file():
        print(f"ERROR: missing GT file: {gt_path}")
        return 2
    if not pred_path.is_file():
        print(f"ERROR: missing prediction file: {pred_path}")
        return 2

    gt_rows = _read_jsonl(gt_path)
    pred_rows = _read_jsonl(pred_path)

    gt_ids = set()
    gt_bad = 0
    for r in gt_rows:
        sid = str(r.get("sample_id", "")).strip()
        ep = str(r.get("expected_parent", "")).strip().upper()
        if not sid or ep not in PARENTS:
            gt_bad += 1
            continue
        gt_ids.add(sid)

    pred_ids = set()
    pred_bad = 0
    for r in pred_rows:
        sid = str(r.get("sample_id", "")).strip()
        pp = str(r.get("predicted_parent", "")).strip().upper()
        c = r.get("confidence")
        ok_c = isinstance(c, (int, float)) and 0.0 <= float(c) <= 1.0
        if not sid or pp not in PARENTS or not ok_c:
            pred_bad += 1
            continue
        pred_ids.add(sid)

    paired = len(gt_ids & pred_ids)
    gt_only = len(gt_ids - pred_ids)
    pred_only = len(pred_ids - gt_ids)

    report = {
        "gt_rows": len(gt_rows),
        "pred_rows": len(pred_rows),
        "gt_invalid_rows": gt_bad,
        "pred_invalid_rows": pred_bad,
        "gt_valid_ids": len(gt_ids),
        "pred_valid_ids": len(pred_ids),
        "paired_ids": paired,
        "gt_only_ids": gt_only,
        "pred_only_ids": pred_only,
    }
    print(json.dumps(report, ensure_ascii=False))

    if gt_bad or pred_bad:
        return 3
    if paired == 0:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

