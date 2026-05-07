from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Build Sasang B-track threshold recalibration candidate from recent runs.")
    ap.add_argument(
        "--base-thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_btrack_daily_thresholds_v1.json",
    )
    ap.add_argument(
        "--go-watch-json",
        type=Path,
        default=root / "reports" / "agct_sasang_go_watch_pack_v1_latest.json",
    )
    ap.add_argument("--max-risk-corr-relax", type=float, default=0.02)
    ap.add_argument("--max-stability-relax", type=float, default=0.02)
    ap.add_argument(
        "--output-thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_btrack_daily_thresholds_recalibrated_v1_latest.json",
    )
    ap.add_argument(
        "--output-report-json",
        type=Path,
        default=root / "reports" / "agct_sasang_threshold_recalibration_report_v1_latest.json",
    )
    ns = ap.parse_args()

    base_doc = _load_json(ns.base_thresholds_json)
    pack = _load_json(ns.go_watch_json)
    runs = [r for r in (pack.get("runs") or []) if isinstance(r, dict)]
    if not runs:
        raise SystemExit("no runs in go/watch pack")

    base_t = (base_doc.get("thresholds") or {}).copy()
    base_risk_min = float(base_t.get("external_risk_corr_min", 0.18))
    base_st_max = float(base_t.get("stability_std_max", 0.05))

    min_obs_risk_corr = min(float(((r.get("metrics") or {}).get("external_risk_corr_observed") or 0.0)) for r in runs)
    max_obs_stability = max(float(((r.get("metrics") or {}).get("stability_std_observed") or 0.0)) for r in runs)

    needed_risk_min = min(base_risk_min, min_obs_risk_corr)
    needed_st_max = max(base_st_max, max_obs_stability)

    tuned_risk_min = max(base_risk_min - float(ns.max_risk_corr_relax), needed_risk_min)
    tuned_st_max = min(base_st_max + float(ns.max_stability_relax), needed_st_max)

    tuned = dict(base_t)
    tuned["external_risk_corr_min"] = round(tuned_risk_min, 6)
    tuned["stability_std_max"] = round(tuned_st_max, 6)

    simulated = []
    for r in runs:
        m = r.get("metrics") or {}
        ext_acc = float(m.get("external_accuracy_observed") or 0.0)
        ext_corr = float(m.get("external_risk_corr_observed") or 0.0)
        st_std = float(m.get("stability_std_observed") or 0.0)
        ts_gap = float(m.get("time_split_gap_observed") or 0.0)
        robust = float(m.get("robustness_observed") or 0.0)
        checks = {
            "external_accuracy_min_ok": ext_acc >= float(tuned.get("external_accuracy_min", 0.0)),
            "external_risk_corr_min_ok": ext_corr >= float(tuned.get("external_risk_corr_min", 0.0)),
            "stability_std_ok": st_std <= float(tuned.get("stability_std_max", 1e9)),
            "time_split_gap_ok": ts_gap <= float(tuned.get("time_split_gap_max", 1e9)),
            "robustness_min_ok": robust >= float(tuned.get("robustness_min", 0.0)),
        }
        simulated.append(
            {
                "seed": r.get("seed"),
                "simulated_decision": "GO_BTRACK" if all(checks.values()) else "REVIEW_REQUIRED",
                "simulated_checks": checks,
            }
        )
    review_count = sum(1 for x in simulated if x["simulated_decision"] == "REVIEW_REQUIRED")

    tuned_doc = {
        "schema": "agct_sasang_btrack_daily_thresholds_v1",
        "track": "B_TRACK",
        "decision_profile": base_doc.get("decision_profile") or "aggressive",
        "thresholds": tuned,
        "notes": [
            "Recalibrated from recent go/watch pack to reduce avoidable REVIEW_REQUIRED noise.",
            "Research-only; requires human review before promotion decisions.",
        ],
    }
    ns.output_thresholds_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_thresholds_json.write_text(json.dumps(tuned_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "agct_sasang_threshold_recalibration_report_v1",
        "generated_at_utc": _utc_now(),
        "base_thresholds_json": str(ns.base_thresholds_json),
        "go_watch_json": str(ns.go_watch_json),
        "base_thresholds": base_t,
        "recalibrated_thresholds": tuned,
        "observed_window": {
            "run_count": len(runs),
            "min_external_risk_corr_observed": round(min_obs_risk_corr, 6),
            "max_stability_std_observed": round(max_obs_stability, 6),
        },
        "simulation": {
            "review_required_count": review_count,
            "runs": simulated,
        },
        "output_thresholds_json": str(ns.output_thresholds_json),
    }
    ns.output_report_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_thresholds_json}")
    print(f"WROTE: {ns.output_report_json}")
    print(f"SIM_REVIEW_REQUIRED={review_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
