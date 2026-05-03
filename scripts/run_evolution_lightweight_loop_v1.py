#!/usr/bin/env python3
"""Lightweight evolution loop (B-track): optional move trigger + per-lens + HITL proposal.

On ``--force`` or when last-day abs(close-to-close return) exceeds thresholds on KOSPI/BTC
CSV series, runs:
  1) build_prophecy_hit_rate_per_lens_v1.py
  2) build_lens_evolution_proposal_v1.py

Writes ``docs/final/artifacts/evolution_lightweight_loop_latest.json`` with trigger diagnostics.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = str(ROOT / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

SCHEMA = "evolution_lightweight_loop_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _last_abs_daily_return(csv_path: Path) -> dict[str, Any] | None:
    if not csv_path.is_file():
        return None
    rows = load_kospi_yf_rows(csv_path)
    if len(rows) < 2:
        return None
    a, b = rows[-2], rows[-1]
    c0, c1 = float(a["close"]), float(b["close"])
    if c0 <= 0:
        return None
    ret = (c1 / c0) - 1.0
    return {
        "prev_date": a.get("date"),
        "last_date": b.get("date"),
        "daily_return": round(ret, 8),
        "abs_daily_return": round(abs(ret), 8),
    }


def _run_script(py: str, script: Path, extra: list[str], *, cwd: Path) -> dict[str, Any]:
    cmd = [py, str(script)] + extra
    cp = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    try:
        rel_s = str(script.resolve().relative_to(cwd.resolve()))
    except ValueError:
        rel_s = str(script)
    return {
        "script": rel_s,
        "exit_code": cp.returncode,
        "stdout_tail": (cp.stdout or "")[-4000:],
        "stderr_tail": (cp.stderr or "")[-4000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument(
        "--kospi-csv",
        type=Path,
        default=None,
        help="Default: research/market_data/kospi_daily_external_yf.csv",
    )
    ap.add_argument(
        "--btc-csv",
        type=Path,
        default=None,
        help="Default: research/market_data/btc_daily_external_yf.csv",
    )
    ap.add_argument("--kospi-abs-ret-threshold", type=float, default=0.012)
    ap.add_argument("--btc-abs-ret-threshold", type=float, default=0.025)
    ap.add_argument("--force", action="store_true", help="Always run downstream scripts.")
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Default: docs/final/artifacts/evolution_lightweight_loop_latest.json",
    )
    ns = ap.parse_args()
    root = Path(ns.workspace_root).expanduser().resolve()
    kospi_csv = ns.kospi_csv or (root / "research/market_data/kospi_daily_external_yf.csv")
    btc_csv = ns.btc_csv or (root / "research/market_data/btc_daily_external_yf.csv")
    out_path = ns.output or (root / "docs/final/artifacts/evolution_lightweight_loop_latest.json")

    k_diag = _last_abs_daily_return(kospi_csv)
    b_diag = _last_abs_daily_return(btc_csv)

    k_trig = (
        k_diag is not None
        and float(k_diag["abs_daily_return"]) >= float(ns.kospi_abs_ret_threshold)
    )
    b_trig = (
        b_diag is not None
        and float(b_diag["abs_daily_return"]) >= float(ns.btc_abs_ret_threshold)
    )
    triggered = bool(ns.force or k_trig or b_trig)

    py = sys.executable
    steps: list[dict[str, Any]] = []
    overall_ok = True
    if triggered:
        s1 = root / "scripts/build_prophecy_hit_rate_per_lens_v1.py"
        s2 = root / "scripts/build_lens_evolution_proposal_v1.py"
        r1 = _run_script(py, s1, [], cwd=root)
        steps.append(r1)
        if r1["exit_code"] != 0:
            overall_ok = False
        r2 = _run_script(py, s2, [], cwd=root)
        steps.append(r2)
        if r2["exit_code"] != 0:
            overall_ok = False

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "triggered": triggered,
        "force": bool(ns.force),
        "thresholds": {
            "kospi_abs_ret": float(ns.kospi_abs_ret_threshold),
            "btc_abs_ret": float(ns.btc_abs_ret_threshold),
        },
        "diagnostics": {
            "kospi_csv": str(kospi_csv),
            "btc_csv": str(btc_csv),
            "kospi_last_bar": k_diag,
            "btc_last_bar": b_diag,
            "kospi_threshold_met": k_trig,
            "btc_threshold_met": b_trig,
        },
        "steps": steps,
        "overall_ok": overall_ok if triggered else True,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} triggered={triggered} ok={payload['overall_ok']}")
    return 0 if (not triggered or overall_ok) else 3


if __name__ == "__main__":
    raise SystemExit(main())
