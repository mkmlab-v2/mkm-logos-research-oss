# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.4, M:0.6}
# Balance: 89
# Purpose: Sweep falsification gate thresholds over proxy/real backtests.
# Keywords: sweep, threshold, falsification, correlation, gate
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROXY_BACKTEST = ART / "btrack_survivor_crash_correlation_backtest_proxy_latest.json"
DEFAULT_REAL_BACKTEST = ART / "btrack_survivor_crash_correlation_backtest_real_latest.json"
DEFAULT_OUTPUT = ART / "btrack_survivor_crash_falsification_threshold_sweep_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": int(p.returncode),
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gate(
    backtest_json: Path,
    out_json: Path,
    min_abs_corr: float,
    max_pvalue: float,
    min_n: int,
    objective_mode: str,
    blend_alpha: float,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_survivor_crash_falsification_gate_v1.py"),
        "--backtest-json",
        str(backtest_json),
        "--output",
        str(out_json),
        "--min-abs-corr",
        str(min_abs_corr),
        "--max-pvalue",
        str(max_pvalue),
        "--min-n",
        str(min_n),
        "--objective-mode",
        objective_mode,
        "--blend-alpha",
        str(blend_alpha),
    ]
    run = _run(cmd)
    doc = _read_json(out_json)
    return {"run": run, "gate": doc}


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep falsification gate threshold over proxy/real survivor backtests.")
    ap.add_argument("--proxy-backtest-json", type=Path, default=DEFAULT_PROXY_BACKTEST)
    ap.add_argument("--real-backtest-json", type=Path, default=DEFAULT_REAL_BACKTEST)
    ap.add_argument("--threshold-grid", type=str, default="0.3,0.4,0.5")
    ap.add_argument("--max-pvalue", type=float, default=0.05)
    ap.add_argument("--min-n", type=int, default=250)
    ap.add_argument("--objective-mode", choices=("return", "crash", "blended"), default="return")
    ap.add_argument("--blend-alpha", type=float, default=0.5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    grid = [float(x.strip()) for x in args.threshold_grid.split(",") if x.strip()]
    blend_alpha = max(0.0, min(1.0, float(args.blend_alpha)))
    rows: list[dict[str, Any]] = []
    for thr in grid:
        proxy_out = ART / f"btrack_survivor_crash_falsification_gate_proxy_thr{str(thr).replace('.', 'p')}_latest.json"
        real_out = ART / f"btrack_survivor_crash_falsification_gate_real_thr{str(thr).replace('.', 'p')}_latest.json"
        proxy_res = _gate(
            args.proxy_backtest_json, proxy_out, thr, args.max_pvalue, args.min_n, args.objective_mode, blend_alpha
        )
        real_res = (
            _gate(args.real_backtest_json, real_out, thr, args.max_pvalue, args.min_n, args.objective_mode, blend_alpha)
            if args.real_backtest_json.is_file()
            else {"run": None, "gate": {}}
        )
        rows.append(
            {
                "min_abs_corr": thr,
                "max_pvalue": float(args.max_pvalue),
                "min_n": int(args.min_n),
                "proxy_decision": ((proxy_res.get("gate") or {}).get("result") or {}).get("decision"),
                "real_decision": ((real_res.get("gate") or {}).get("result") or {}).get("decision"),
                "proxy_gate_path": str(proxy_out),
                "real_gate_path": str(real_out) if args.real_backtest_json.is_file() else None,
                "proxy_run": proxy_res.get("run"),
                "real_run": real_res.get("run"),
            }
        )

    out = {
        "schema": "btrack_survivor_crash_falsification_threshold_sweep_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {
            "proxy_backtest_json": str(args.proxy_backtest_json),
            "real_backtest_json": str(args.real_backtest_json),
            "real_backtest_available": args.real_backtest_json.is_file(),
            "threshold_grid": grid,
            "max_pvalue": float(args.max_pvalue),
            "min_n": int(args.min_n),
            "objective_mode": args.objective_mode,
            "blend_alpha": blend_alpha,
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
