#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build AGCT B-track sensitivity report from GO watch pack.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--watch-pack-json",
        type=Path,
        default=root / "reports" / "agct_sasang_go_watch_pack_v1_latest.json",
    )
    ap.add_argument(
        "--thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_btrack_daily_thresholds_v1.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_sensitivity_report_v1_latest.json",
    )
    ns = ap.parse_args()

    watch = json.loads(ns.watch_pack_json.read_text(encoding="utf-8"))
    tdoc = json.loads(ns.thresholds_json.read_text(encoding="utf-8"))
    th = tdoc["thresholds"]
    runs = watch.get("runs", [])
    n = len(runs)
    if n == 0:
        raise SystemExit("No runs found in watch pack.")

    fail_counts = {
        "external_accuracy_min_ok": 0,
        "external_risk_corr_min_ok": 0,
        "stability_std_ok": 0,
        "time_split_gap_ok": 0,
        "robustness_min_ok": 0,
    }
    ext_corr_vals = []
    robustness_vals = []
    stability_vals = []
    for r in runs:
        checks = r.get("checks", {})
        m = r.get("metrics", {})
        for k in fail_counts:
            if checks.get(k) is False:
                fail_counts[k] += 1
        ext_corr_vals.append(float(m.get("external_risk_corr_observed", 0.0)))
        robustness_vals.append(float(m.get("robustness_observed", 0.0)))
        stability_vals.append(float(m.get("stability_std_observed", 0.0)))

    dominant = sorted(fail_counts.items(), key=lambda kv: kv[1], reverse=True)[0]
    payload = {
        "schema": "agct_sasang_sensitivity_report_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "watch_pack_json": str(ns.watch_pack_json.resolve()),
            "thresholds_json": str(ns.thresholds_json.resolve()),
        },
        "summary": {
            "n_runs": n,
            "go_count": int(watch.get("summary", {}).get("go_count", 0)),
            "go_ratio": float(watch.get("summary", {}).get("go_count", 0)) / n,
            "dominant_failure_gate": dominant[0],
            "dominant_failure_count": dominant[1],
        },
        "failure_counts": fail_counts,
        "metric_stats": {
            "external_risk_corr": {
                "mean": _mean(ext_corr_vals),
                "min": min(ext_corr_vals),
                "max": max(ext_corr_vals),
                "threshold": float(th["external_risk_corr_min"]),
            },
            "robustness": {
                "mean": _mean(robustness_vals),
                "min": min(robustness_vals),
                "max": max(robustness_vals),
                "threshold": float(th.get("robustness_min", 0.0)),
            },
            "stability_std": {
                "mean": _mean(stability_vals),
                "min": min(stability_vals),
                "max": max(stability_vals),
                "threshold_max": float(th["stability_std_max"]),
            },
        },
        "priority_actions": [
            "Prioritize external_risk_corr uplift; it is the most frequent fail gate.",
            "Constrain stability_std under repeated seed perturbation.",
            "Keep robustness >= robustness_min while improving external_risk_corr.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} dominant_fail={dominant[0]} count={dominant[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
