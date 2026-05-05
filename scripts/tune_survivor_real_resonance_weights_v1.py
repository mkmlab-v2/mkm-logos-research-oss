# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.9, K:0.5, M:0.6}
# Balance: 89
# Purpose: Tune real resonance builder weights to maximize research correlation objective.
# Keywords: tune, weight, resonance, backtest, optimization
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

DEFAULT_REAL_JSONL = ART / "global_atom_survivor_resonance_daily_real_latest.jsonl"
DEFAULT_REAL_BACKTEST = ART / "btrack_survivor_crash_correlation_backtest_real_latest.json"
DEFAULT_OUT = ART / "btrack_survivor_real_resonance_tuning_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {"cmd": cmd, "returncode": int(p.returncode), "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _score_from_backtest(doc: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    analysis = doc.get("analysis") if isinstance(doc.get("analysis"), dict) else {}
    kospi = analysis.get("kospi") if isinstance(analysis.get("kospi"), dict) else {}
    best = kospi.get("best_abs_corr_row") if isinstance(kospi.get("best_abs_corr_row"), dict) else {}
    corr = _safe_float(best.get("return_corr"))
    p = _safe_float(kospi.get("best_return_corr_permutation_pvalue"))
    # Optimize for higher |corr| and lower p-value.
    objective = abs(corr) - 0.1 * p
    return objective, {"kospi_best_corr": corr, "kospi_pvalue": p, "kospi_best_lag": best.get("lag_days")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune real resonance builder weights.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--real-jsonl", type=Path, default=DEFAULT_REAL_JSONL)
    ap.add_argument("--real-backtest", type=Path, default=DEFAULT_REAL_BACKTEST)
    args = ap.parse_args()

    grid_candidate = [0.4, 0.6, 0.8]
    grid_flow = [0.1, 0.3, 0.5]
    grid_temporal = [0.1, 0.2]
    rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for wc in grid_candidate:
        for wf in grid_flow:
            for wt in grid_temporal:
                build_cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "build_global_atom_survivor_resonance_daily_real_v1.py"),
                    "--w-candidate",
                    str(wc),
                    "--w-flow",
                    str(wf),
                    "--w-temporal",
                    str(wt),
                    "--output-jsonl",
                    str(args.real_jsonl),
                ]
                run_build = _run(build_cmd)
                bt_cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "run_btrack_survivor_crash_correlation_backtest_v1.py"),
                    "--resonance-jsonl",
                    str(args.real_jsonl),
                    "--output",
                    str(args.real_backtest),
                ]
                run_bt = _run(bt_cmd)
                bt_doc = _read_json(args.real_backtest)
                objective, metrics = _score_from_backtest(bt_doc)
                row = {
                    "weights": {"w_candidate": wc, "w_flow": wf, "w_temporal": wt},
                    "objective": objective,
                    "metrics": metrics,
                    "build_returncode": run_build["returncode"],
                    "backtest_returncode": run_bt["returncode"],
                }
                rows.append(row)
                if best is None or objective > _safe_float(best.get("objective")):
                    best = row

    out = {
        "schema": "btrack_survivor_real_resonance_tuning_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "grid": {"w_candidate": grid_candidate, "w_flow": grid_flow, "w_temporal": grid_temporal},
        "best": best,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    if best:
        w = best["weights"]
        print(f"best_weights=candidate:{w['w_candidate']} flow:{w['w_flow']} temporal:{w['w_temporal']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
