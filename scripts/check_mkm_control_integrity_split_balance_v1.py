#!/usr/bin/env python3
"""Check split/balance rules for MKM control-integrity golden set v1."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_golden_set_v1_1000.jsonl"
DEFAULT_REPORT = WORKSPACE_ROOT / "reports" / "mkm_control_integrity_golden_set_v1_balance_latest.json"

SPLITS = ("train", "validation", "test", "locked_eval")
SPLIT_TARGETS = {"train": 0.70, "validation": 0.15, "test": 0.10, "locked_eval": 0.05}


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _approx_equal(actual_ratio: float, target_ratio: float, tol: float) -> bool:
    return abs(actual_ratio - target_ratio) <= tol


def _response_type_from_context(ctx: str) -> str:
    marker = "response_type="
    if marker in ctx:
        return ctx.split(marker, 1)[1].strip()
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Check split/balance for golden set v1")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_JSONL), help="Input JSONL path")
    ap.add_argument("--report-out", dest="report_out", default=str(DEFAULT_REPORT), help="Output report path")
    ap.add_argument("--split-tol", type=float, default=0.02, help="Allowed split ratio tolerance")
    ap.add_argument("--group-ratio-max-gap", type=float, default=0.12, help="Allowed max ratio gap for domain/risk/response")
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    report_out = _as_abs(args.report_out)
    if not input_path.is_file():
        print(f"input not found: {input_path}")
        return 1

    total = 0
    split_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    response_counter: Counter[str] = Counter()
    split_domain: dict[str, Counter[str]] = defaultdict(Counter)
    errors: list[str] = []

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_no}: invalid json: {exc}")
                continue

            total += 1
            split = str(row.get("split", "unknown"))
            domain = str(row.get("domain", "unknown"))
            risk = str(row.get("risk_level", "unknown"))
            ctx = str(row.get("context", ""))
            response_type = _response_type_from_context(ctx)
            split_counter[split] += 1
            domain_counter[domain] += 1
            risk_counter[risk] += 1
            response_counter[response_type] += 1
            split_domain[split][domain] += 1

    if total == 0:
        print("empty dataset")
        return 2

    split_checks: dict[str, dict[str, Any]] = {}
    for split in SPLITS:
        actual = split_counter.get(split, 0) / total
        target = SPLIT_TARGETS[split]
        split_checks[split] = {
            "count": split_counter.get(split, 0),
            "actual_ratio": round(actual, 4),
            "target_ratio": target,
            "pass": _approx_equal(actual, target, args.split_tol),
        }
        if not split_checks[split]["pass"]:
            errors.append(f"split ratio out of tolerance: {split}")

    def ratio_gap(counter: Counter[str]) -> float:
        if not counter:
            return 1.0
        ratios = [v / total for v in counter.values()]
        return max(ratios) - min(ratios)

    domain_gap = ratio_gap(domain_counter)
    risk_gap = ratio_gap(risk_counter)
    response_gap = ratio_gap(response_counter)
    balance_pass = all(g <= args.group_ratio_max_gap for g in (domain_gap, risk_gap, response_gap))
    if not balance_pass:
        errors.append("group balance gap exceeded threshold")

    report = {
        "schema": "mkm_control_integrity_golden_set_v1_balance_report",
        "input": str(input_path),
        "total_rows": total,
        "split_policy": {"targets": SPLIT_TARGETS, "tolerance": args.split_tol},
        "group_balance_policy": {"ratio_max_gap": args.group_ratio_max_gap},
        "distribution": {
            "split": dict(split_counter),
            "domain": dict(domain_counter),
            "risk_level": dict(risk_counter),
            "response_type": dict(response_counter),
            "split_x_domain": {k: dict(v) for k, v in split_domain.items()},
        },
        "checks": {
            "split_checks": split_checks,
            "domain_ratio_gap": round(domain_gap, 4),
            "risk_ratio_gap": round(risk_gap, 4),
            "response_ratio_gap": round(response_gap, 4),
            "balance_pass": balance_pass,
        },
        "errors": errors,
        "ok": len(errors) == 0,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    with report_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"rows={total}")
    print(f"errors={len(errors)}")
    print(f"report={report_out}")
    return 0 if len(errors) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
