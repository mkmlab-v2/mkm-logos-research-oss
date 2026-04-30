#!/usr/bin/env python3
"""Build alert artifact from genius reasoning benchmark robustness signals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_BENCH = ART / "genius_reasoning_benchmark_report_latest.json"
DEFAULT_OUT = ART / "genius_reasoning_benchmark_alert_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benchmark-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--warn-robust-score", type=float, default=90.0)
    ap.add_argument("--warn-calibration-gap", type=float, default=0.15)
    ap.add_argument("--pre-alert-robust-score", type=float, default=82.0)
    args = ap.parse_args()

    bench = _read_json(args.benchmark_json)
    robustness = bench.get("robustness") if isinstance(bench.get("robustness"), dict) else {}
    summary = bench.get("summary") if isinstance(bench.get("summary"), dict) else {}
    robust_status = str(robustness.get("robust_benchmark_status") or "UNKNOWN")
    robust_score_100 = float(robustness.get("robust_score_100") or 0.0)
    calibration_gap = float(robustness.get("calibration_gap") or 0.0)
    coverage_gate_pass = bool(robustness.get("coverage_gate_pass"))

    reasons: list[str] = []
    severity = "INFO"
    pre_alert_reasons: list[str] = []
    if robust_status != "PASS":
        severity = "CRITICAL"
        reasons.append("robust_benchmark_not_pass")
    if robust_score_100 < float(args.warn_robust_score):
        severity = "WARNING" if severity == "INFO" else severity
        reasons.append("robust_score_below_warn_threshold")
    if calibration_gap > float(args.warn_calibration_gap):
        severity = "WARNING" if severity == "INFO" else severity
        reasons.append("calibration_gap_above_warn_threshold")
    if not coverage_gate_pass:
        severity = "CRITICAL" if robust_status != "PASS" else "WARNING"
        reasons.append("coverage_gate_not_pass")
    if robust_score_100 <= float(args.pre_alert_robust_score):
        pre_alert_reasons.append("robust_score_near_warn_threshold")

    out = {
        "schema": "genius_reasoning_benchmark_alert_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "benchmark_json": str(args.benchmark_json).replace("\\", "/"),
        },
        "thresholds": {
            "warn_robust_score": float(args.warn_robust_score),
            "warn_calibration_gap": float(args.warn_calibration_gap),
            "pre_alert_robust_score": float(args.pre_alert_robust_score),
        },
        "current": {
            "benchmark_status": summary.get("benchmark_status"),
            "robust_benchmark_status": robust_status,
            "robust_score_100": robust_score_100,
            "calibration_gap": calibration_gap,
            "coverage_gate_pass": coverage_gate_pass,
        },
        "alert": {
            "severity": severity,
            "active": bool(reasons),
            "reasons": reasons,
        },
        "pre_alert": {
            "active": bool(pre_alert_reasons),
            "reasons": pre_alert_reasons,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "severity": severity,
                "active": bool(reasons),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
