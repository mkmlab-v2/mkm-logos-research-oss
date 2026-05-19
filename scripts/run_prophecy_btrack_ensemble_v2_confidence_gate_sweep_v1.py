#!/usr/bin/env python3
"""Sweep per-date-min-confidence for v2 180d directions (B-track)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_CHAIN = ROOT / "scripts" / "run_prophecy_btrack_ensemble_v2_eval_chain_v1.py"
V2_GATES_LATEST = ROOT / "reports/prophecy_promotion_gates_ensemble_v2_lane_v1_latest.json"
DEFAULT_DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_ensemble_v2_confidence_gate_sweep_v1_latest.json"
DEFAULT_DIR = ROOT / "reports/btrack_ensemble_v2_confidence_gate_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gate_mean(gates: dict[str, Any] | None, track: str, gate_id: str) -> float | None:
    if not isinstance(gates, dict):
        return None
    block = (gates.get("tracks") or {}).get(track) or {}
    for g in block.get("gates") or []:
        if isinstance(g, dict) and g.get("gate_id") == gate_id:
            v = (g.get("observed") or {}).get("mean_test_accuracy")
            if isinstance(v, (int, float)):
                return float(v)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confidence-grid", default="0,0.1,0.15,0.2,0.25,0.3,0.35,0.4")
    ap.add_argument("--neutral-bps", type=float, default=1.5)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_DIRS)
    ap.add_argument("--sweep-dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    grid = [float(x.strip()) for x in str(args.confidence_grid).split(",") if x.strip()]
    args.sweep_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_key = (-1.0, -1.0)
    first_pass: dict[str, Any] | None = None

    for conf in grid:
        slug = str(conf).replace(".", "p")
        gates_path = args.sweep_dir / f"gates_conf_{slug}.json"
        cmd = [
            sys.executable,
            str(EVAL_CHAIN),
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--neutral-bps",
            str(args.neutral_bps),
            "--per-date-v2-json",
            str(args.per_date_json),
            "--per-date-min-confidence",
            str(conf),
            "--instrument-btc-policies",
            "prior,panel",
            "--instrument-include-panel-kospi-mode",
            "--skip-baseline",
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if V2_GATES_LATEST.is_file():
            shutil.copy2(V2_GATES_LATEST, gates_path)
        gates = json.loads(gates_path.read_text(encoding="utf-8")) if gates_path.is_file() else {}
        lm = _gate_mean(gates, "per_date_lens", "lens_wf_mean_test_accuracy")
        im = _gate_mean(gates, "instrument_combo", "instrument_wf_mean_test_accuracy")
        comb = bool(gates.get("combined_all_passed"))
        row = {
            "per_date_min_confidence": conf,
            "exit_code": rc,
            "lens_mean": lm,
            "instrument_mean": im,
            "combined_all_passed": comb,
            "gates_json": str(gates_path),
        }
        rows.append(row)
        print(f"conf>={conf} lens={lm} inst={im} combined={comb}", file=sys.stderr)
        if comb and first_pass is None:
            first_pass = row
        if lm is not None and im is not None:
            key = (float(lm) + float(im), min(float(lm), float(im)))
            if key > best_key:
                best_key = key
                best = row

    doc = {
        "schema": "btrack_ensemble_v2_confidence_gate_sweep_v1",
        "ts_utc": _utc_now(),
        "neutral_bps": float(args.neutral_bps),
        "per_date_json": str(args.per_date_json),
        "rows": rows,
        "best_by_lex": best,
        "first_combined_all_passed": first_pass,
    }
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0 if all(int(r["exit_code"]) == 0 for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
