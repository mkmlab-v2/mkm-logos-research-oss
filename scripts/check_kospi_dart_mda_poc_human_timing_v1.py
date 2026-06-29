#!/usr/bin/env python3
"""Validate Gate B human timing sheet — compute savings when trials are filled.

Exit 0: awaiting trials OR gate_b_pass true.
Exit 1: trials filled but mean_savings_ratio < target.

Reproduce:
  py scripts/check_kospi_dart_mda_poc_human_timing_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports/kospi_dart_mda_poc_human_timing_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_dart_mda_poc_human_timing_check_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate(doc: dict[str, Any]) -> tuple[str, dict[str, Any], int]:
    target = float(doc.get("target_savings_ratio_min") or 0.20)
    trials = doc.get("trials") or []
    filled: list[dict[str, Any]] = []
    ratios: list[float] = []

    for trial in trials:
        manual = trial.get("manual_sec")
        poc = trial.get("poc_click_verify_sec")
        if manual is None or poc is None:
            continue
        try:
            m = float(manual)
            p = float(poc)
        except (TypeError, ValueError):
            continue
        if m <= 0:
            continue
        ratio = (m - p) / m
        trial = dict(trial)
        trial["savings_ratio"] = round(ratio, 4)
        filled.append(trial)
        ratios.append(ratio)

    if len(filled) < len(trials):
        status = "awaiting_commander_trials"
        gate_pass = None
        exit_code = 0
    else:
        mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
        gate_pass = mean_ratio >= target
        status = "gate_b_pass" if gate_pass else "gate_b_fail"
        exit_code = 0 if gate_pass else 1

    mean_ratio_val = round(sum(ratios) / len(ratios), 4) if ratios else None
    report = {
        "schema": "kospi_dart_mda_poc_human_timing_check_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "status": status,
        "target_savings_ratio_min": target,
        "trials_filled": len(filled),
        "trials_total": len(trials),
        "aggregate": {
            "mean_savings_ratio": mean_ratio_val,
            "gate_b_pass": gate_pass,
        },
        "trials": filled if filled else trials,
        "reproduce": "py scripts/check_kospi_dart_mda_poc_human_timing_v1.py",
    }
    return status, report, exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.in_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_timing_sheet"}, ensure_ascii=False))
        return 1

    doc = json.loads(args.in_path.read_text(encoding="utf-8-sig"))
    status, report, exit_code = evaluate(doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": exit_code == 0, "status": status, "artifact": str(args.out)}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
