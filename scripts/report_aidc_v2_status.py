#!/usr/bin/env python3
"""Summarize latest AIDC v2 loop status from artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
GATE = ART / "aidc_kpi_gate_v2.json"
PERF = ART / "aidc_perf_ab_summary_v2.json"
POWER = ART / "power_profile_v2.csv"
OUT_JSON = ART / "aidc_v2_status_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_uplifts(power_csv: Path) -> list[float]:
    rows = list(csv.DictReader(power_csv.open(encoding="utf-8")))
    pairs: list[float] = []
    baseline = None
    for r in rows:
        label = (r.get("label") or "").strip().lower()
        if label == "baseline":
            baseline = r
            continue
        if label == "treatment" and baseline is not None:
            try:
                b = float(baseline.get("perf_per_w") or 0.0)
                t = float(r.get("perf_per_w") or 0.0)
                if b > 0:
                    pairs.append(((t - b) / b) * 100.0)
            except ValueError:
                pass
            baseline = None
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description="Build AIDC v2 status summary.")
    ap.add_argument("--window", type=int, default=20, help="Recent uplift window size")
    ap.add_argument("--output", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    gate = _load_json(GATE)
    perf = _load_json(PERF)
    uplifts = _load_uplifts(POWER)
    recent = uplifts[-max(1, args.window) :] if uplifts else []

    out = {
        "schema": "aidc_v2_status_summary_v1",
        "gate_generated_at_utc": gate.get("generated_at_utc"),
        "decision": (gate.get("go_no_go") or {}).get("decision"),
        "reasons": (gate.get("go_no_go") or {}).get("reasons", []),
        "accuracy": (gate.get("kpi") or {}).get("accuracy", {}),
        "accuracy_target": (gate.get("kpi") or {}).get("accuracy_significance_target", {}),
        "perf_latest_uplift_pct": perf.get("uplift_perf_per_w_pct"),
        "perf_recent_window": {
            "n": len(recent),
            "mean_uplift_pct": round(mean(recent), 6) if recent else None,
            "min_uplift_pct": round(min(recent), 6) if recent else None,
            "max_uplift_pct": round(max(recent), 6) if recent else None,
            "last5_uplift_pct": [round(x, 6) for x in recent[-5:]] if recent else [],
        },
    }

    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
