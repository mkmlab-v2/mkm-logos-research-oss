#!/usr/bin/env python3
"""Build a compact week4 ops dashboard from smartfarm replay artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build smartfarm week4 ops dashboard JSON/MD.")
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
    )
    parser.add_argument(
        "--kpi-sweep-csv",
        default="data/smartfarm_rda_extract_v1/out/rain_gate_threshold_sweep_v1.csv",
    )
    parser.add_argument(
        "--guard-summary-json",
        default="data/smartfarm_rda_extract_v1/out/week4_data_guard_summary_v1.json",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_week4_ops_dashboard_v1.json",
    )
    parser.add_argument(
        "--output-md",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_week4_ops_dashboard_v1.md",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = _parse_args()
    zone_path = Path(args.zone_weather_csv)
    sweep_path = Path(args.kpi_sweep_csv)
    guard_path = Path(args.guard_summary_json)
    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    zone = pd.read_csv(zone_path)
    sweep = pd.read_csv(sweep_path)
    guard = _read_json(guard_path)

    for col in ("rain_mm_1h", "rain_mm_12h"):
        if col in zone.columns:
            zone[col] = pd.to_numeric(zone[col], errors="coerce")

    zone["agmet_ts_local"] = pd.to_datetime(zone["agmet_ts_local"], errors="coerce")

    best = (
        sweep.sort_values(
            by=["kpi06_rain_loss_avoidance_ratio", "gate_precision_like"],
            ascending=[False, False],
            na_position="last",
        )
        .head(1)
        .to_dict(orient="records")
    )
    best_row = best[0] if best else {}

    dashboard = {
        "schema": "smartfarm_week4_ops_dashboard_v1",
        "status": "PASS" if guard.get("overall_ok", False) else "WARN_OR_FAIL",
        "counts": {
            "rows": int(len(zone)),
            "farm_count": int(zone["farm_id"].nunique()) if "farm_id" in zone.columns else 0,
            "zone_count": int(zone["zone_id"].nunique()) if "zone_id" in zone.columns else 0,
            "station_count": int(zone["agmet_station_name"].nunique()) if "agmet_station_name" in zone.columns else 0,
        },
        "weather_snapshot": {
            "rain_mm_1h_mean": float(zone["rain_mm_1h"].mean()) if "rain_mm_1h" in zone.columns else None,
            "rain_mm_12h_mean": float(zone["rain_mm_12h"].mean()) if "rain_mm_12h" in zone.columns else None,
            "start_local": zone["agmet_ts_local"].min().isoformat() if zone["agmet_ts_local"].notna().any() else None,
            "end_local": zone["agmet_ts_local"].max().isoformat() if zone["agmet_ts_local"].notna().any() else None,
        },
        "kpi06_best_candidate": best_row,
        "guard_summary_ref": str(guard_path),
        "guard_status": guard.get("status"),
        "notes": [
            "This dashboard is replay-lane evidence and does not imply live auto-control readiness alone.",
            "Live deployment requires forecast feed validation and telemetry gates per AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml.",
        ],
    }

    out_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Smartfarm Week4 Ops Dashboard (Replay)",
        "",
        f"- status: `{dashboard['status']}`",
        f"- rows: `{dashboard['counts']['rows']}`",
        f"- farm_count: `{dashboard['counts']['farm_count']}` / zone_count: `{dashboard['counts']['zone_count']}` / station_count: `{dashboard['counts']['station_count']}`",
        f"- window: `{dashboard['weather_snapshot']['start_local']}` -> `{dashboard['weather_snapshot']['end_local']}`",
        "",
        "## KPI-06 best candidate",
        f"- threshold_mm_12h: `{best_row.get('threshold_mm_12h')}`",
        f"- kpi06_rain_loss_avoidance_ratio: `{best_row.get('kpi06_rain_loss_avoidance_ratio')}`",
        f"- gate_precision_like: `{best_row.get('gate_precision_like')}`",
        "",
        "## Guard",
        f"- guard_status: `{dashboard['guard_status']}`",
        f"- guard_summary_ref: `{dashboard['guard_summary_ref']}`",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"[ok] dashboard json -> {out_json}")
    print(f"[ok] dashboard md -> {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

