#!/usr/bin/env python3
"""Evaluate B-Track promotion gate from latest quality report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_quality_latest.json"
DEFAULT_GATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "promotion_gate_template.json"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_promotion_gate_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate B-Track promotion gate")
    ap.add_argument("--report", default=str(DEFAULT_REPORT), help="Quality report JSON")
    ap.add_argument("--gate", default=str(DEFAULT_GATE), help="Gate template JSON")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output gate decision JSON")
    args = ap.parse_args()

    report_path = _abs(args.report)
    gate_path = _abs(args.gate)
    out_path = _abs(args.out)

    if not report_path.is_file():
        print(f"ERROR: missing report: {report_path}")
        return 2
    if not gate_path.is_file():
        print(f"ERROR: missing gate template: {gate_path}")
        return 2

    report = _jread(report_path)
    gate = _jread(gate_path)

    m = report.get("metrics", {})
    t = gate.get("thresholds", {})

    repro = m.get("reproducibility_match_rate")
    res = m.get("resolution_confidence_delta_b_minus_a")
    contam = m.get("contamination_snr_delta_b_minus_a")

    th_repro = t.get("reproducibility_match_rate_min", 0.8)
    th_res = t.get("resolution_confidence_delta_min", 0.0)
    th_contam = t.get("contamination_snr_delta_min", 0.0)

    checks = {
        "reproducibility_ok": isinstance(repro, (int, float)) and repro >= th_repro,
        "resolution_ok": isinstance(res, (int, float)) and res >= th_res,
        "contamination_ok": isinstance(contam, (int, float)) and contam >= th_contam,
    }

    decision = "pass" if all(checks.values()) else "hold"
    out = {
        "schema": "btrack_promotion_gate_result_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"report": str(report_path), "gate_template": str(gate_path)},
        "metrics": {
            "reproducibility_match_rate": repro,
            "resolution_confidence_delta_b_minus_a": res,
            "contamination_snr_delta_b_minus_a": contam,
        },
        "thresholds": {
            "reproducibility_match_rate_min": th_repro,
            "resolution_confidence_delta_min": th_res,
            "contamination_snr_delta_min": th_contam,
        },
        "checks": checks,
        "decision": decision,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: gate decision={decision}")
    print(f"out: {out_path}")
    return 0 if decision == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
