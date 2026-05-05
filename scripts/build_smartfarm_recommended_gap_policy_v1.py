#!/usr/bin/env python3
"""Build recommended gap recovery policy decision artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend smartfarm gap policy from simulation + impact artifacts.")
    parser.add_argument(
        "--policy-simulation-csv",
        default="data/smartfarm_rda_extract_v1/out/gap_recovery_policy_simulation_v1.csv",
    )
    parser.add_argument(
        "--impact-csv",
        default="data/smartfarm_rda_extract_v1/out/gap_policy_kpi_impact_v1.csv",
    )
    parser.add_argument(
        "--impact-summary-json",
        default="data/smartfarm_rda_extract_v1/out/gap_policy_kpi_impact_summary_v1.json",
    )
    parser.add_argument(
        "--min-kpi06-delta",
        type=float,
        default=-0.005,
        help="Minimum acceptable delta_kpi06 (hybrid-baseline).",
    )
    parser.add_argument(
        "--min-precision-delta",
        type=float,
        default=0.0001,
        help="Minimum required delta_gate_precision_like.",
    )
    parser.add_argument(
        "--max-coverage-loss-rows",
        type=int,
        default=500,
        help="Maximum acceptable rows dropped by skip policy in hybrid.",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/recommended_policy_v1.json",
    )
    parser.add_argument(
        "--output-md",
        default="data/smartfarm_rda_extract_v1/out/recommended_policy_v1.md",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def main() -> int:
    args = _parse_args()
    sim_path = _expect_exists(Path(args.policy_simulation_csv))
    impact_path = _expect_exists(Path(args.impact_csv))
    impact_summary_path = _expect_exists(Path(args.impact_summary_json))
    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    sim = pd.read_csv(sim_path)
    impact = pd.read_csv(impact_path)
    impact_summary = json.loads(impact_summary_path.read_text(encoding="utf-8"))

    # Aggregate impact deltas across thresholds.
    avg_delta_kpi06 = float(impact["delta_kpi06"].mean())
    avg_delta_precision = float(impact["delta_gate_precision_like"].mean())
    avg_delta_trigger_rate = float(impact["delta_gate_trigger_rate"].mean())

    row_counts = impact_summary.get("row_counts", {})
    rows_dropped = int(row_counts.get("rows_dropped_by_skip", 0))

    # Candidate policies from simulation
    sim_index = {row["policy"]: row for row in sim.to_dict(orient="records")}
    ffill = sim_index.get("ffill", {})
    skip = sim_index.get("skip", {})
    flag_only = sim_index.get("flag_only", {})

    pass_kpi = avg_delta_kpi06 >= args.min_kpi06_delta
    pass_precision = avg_delta_precision >= args.min_precision_delta
    pass_coverage = rows_dropped <= args.max_coverage_loss_rows

    if pass_kpi and pass_precision and pass_coverage:
        recommendation = "hybrid_skip_large_ffill_small"
        rationale = "Hybrid passes KPI/precision/coverage constraints."
    elif pass_kpi and pass_coverage:
        recommendation = "skip"
        rationale = "Hybrid precision uplift too small; prefer safest skip policy within coverage budget."
    else:
        recommendation = "flag_only"
        rationale = "Guardrail constraints not met; remain monitoring-only until data quality improves."

    artifact = {
        "schema": "smartfarm_recommended_policy_v1",
        "recommendation": recommendation,
        "rationale": rationale,
        "decision_inputs": {
            "avg_delta_kpi06": avg_delta_kpi06,
            "avg_delta_gate_precision_like": avg_delta_precision,
            "avg_delta_gate_trigger_rate": avg_delta_trigger_rate,
            "rows_dropped_by_skip": rows_dropped,
        },
        "decision_constraints": {
            "min_kpi06_delta": args.min_kpi06_delta,
            "min_precision_delta": args.min_precision_delta,
            "max_coverage_loss_rows": args.max_coverage_loss_rows,
            "pass_kpi": pass_kpi,
            "pass_precision": pass_precision,
            "pass_coverage": pass_coverage,
        },
        "policy_snapshot": {
            "ffill": ffill,
            "skip": skip,
            "flag_only": flag_only,
        },
        "references": {
            "policy_simulation_csv": str(sim_path),
            "impact_csv": str(impact_path),
            "impact_summary_json": str(impact_summary_path),
        },
        "notes": [
            "Recommendation is replay-lane guidance only.",
            "Live control policy changes require human sign-off and telemetry/forecast validation.",
        ],
    }
    out_json.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Recommended Gap Policy v1",
        "",
        f"- recommendation: `{recommendation}`",
        f"- rationale: {rationale}",
        "",
        "## Decision Inputs",
        f"- avg_delta_kpi06: `{avg_delta_kpi06}`",
        f"- avg_delta_gate_precision_like: `{avg_delta_precision}`",
        f"- avg_delta_gate_trigger_rate: `{avg_delta_trigger_rate}`",
        f"- rows_dropped_by_skip: `{rows_dropped}`",
        "",
        "## Constraints",
        f"- min_kpi06_delta: `{args.min_kpi06_delta}` / pass: `{pass_kpi}`",
        f"- min_precision_delta: `{args.min_precision_delta}` / pass: `{pass_precision}`",
        f"- max_coverage_loss_rows: `{args.max_coverage_loss_rows}` / pass: `{pass_coverage}`",
        "",
        "## Safety Note",
        "- Replay recommendation only. Live operation requires human sign-off and sensor/forecast gate validation.",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"[ok] recommendation -> {out_json}")
    print(f"[ok] report -> {out_md}")
    print(f"[ok] selected: {recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

