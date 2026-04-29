#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import List


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep KPI forward-label tolerance and compare reports.")
    ap.add_argument("--workspace-root", type=Path, default=Path("c:/workspace"))
    ap.add_argument("--tolerances-hours", type=int, nargs="+", default=[1, 3, 6])
    ap.add_argument("--kpi-intraday-step-minutes", type=int, default=60)
    ap.add_argument("--out-json", type=Path, default=Path("c:/workspace/docs/final/artifacts/emotion_label_tolerance_sweep_latest.json"))
    args = ap.parse_args()

    ws = args.workspace_root
    chain = ws / "scripts" / "run_emotion_weight_memory_weekly_chain.ps1"
    report_path = ws / "docs" / "final" / "artifacts" / "emotion_weight_memory_weekly_report_latest.json"
    rows = []
    for tol in args.tolerances_hours:
        _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(chain),
                "-BuildOperationalInputs",
                "-KpiIntradayStepMinutes",
                str(args.kpi_intraday_step_minutes),
                "-KpiForwardToleranceHours",
                str(tol),
            ]
        )
        rpt = _read_json(report_path)
        rows.append(
            {
                "tolerance_hours": tol,
                "overall_recommended": rpt.get("source_gate", {}).get("overall_recommended"),
                "combined_recommended": rpt.get("source_gate", {}).get("combined_recommended"),
                "primary_source": rpt.get("source_gate", {}).get("primary_source"),
                "primary_n_usable": rpt.get("source_gate", {}).get("primary_n_usable"),
                "corr_valence_vs_forward_pnl_1d": rpt.get("metrics", {}).get("corr_valence_vs_forward_pnl_1d"),
                "coverage_ratio": rpt.get("coverage_ratio"),
            }
        )

    out = {"schema_version": "emotion_label_tolerance_sweep_v1", "kpi_intraday_step_minutes": args.kpi_intraday_step_minutes, "rows": rows}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
