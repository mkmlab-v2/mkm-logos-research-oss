# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.6, M:0.6}
# Balance: 88
# Purpose: One-click survivor resonance operational bundle (tune->build->chain->sweep->exploratory gate).
# Keywords: bundle, survivor, resonance, tuning, gate, sweep
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
DEFAULT_OUTPUT = ART / "survivor_resonance_operational_bundle_latest.json"
DEFAULT_EXPLORATORY_MIN_ABS_CORR = 0.08
VALIDATED_MAX_GO_MIN_ABS_CORR = 0.082


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {"cmd": cmd, "returncode": int(p.returncode), "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _threshold_tag(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run survivor resonance operational bundle.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--exploratory-min-abs-corr", type=float, default=DEFAULT_EXPLORATORY_MIN_ABS_CORR)
    ap.add_argument("--max-pvalue", type=float, default=0.05)
    ap.add_argument("--min-n", type=int, default=250)
    args = ap.parse_args()
    gate_tag = _threshold_tag(float(args.exploratory_min_abs_corr))
    gate_output_path = ART / f"btrack_survivor_crash_falsification_gate_real_thr{gate_tag}_latest.json"

    runs: dict[str, Any] = {}
    steps = [
        ("tuning", [sys.executable, str(ROOT / "scripts" / "tune_survivor_real_resonance_weights_v1.py")]),
        ("direct_mapping", [sys.executable, str(ROOT / "scripts" / "build_survivor_w3_direct_mapping_v1.py")]),
        ("build_real", [sys.executable, str(ROOT / "scripts" / "build_global_atom_survivor_resonance_daily_real_v1.py")]),
        ("falsification_chain", [sys.executable, str(ROOT / "scripts" / "run_survivor_resonance_falsification_chain_v1.py")]),
        ("threshold_sweep", [sys.executable, str(ROOT / "scripts" / "sweep_survivor_crash_falsification_thresholds_v1.py"), "--threshold-grid", "0.3,0.4,0.5"]),
        (
            "exploratory_gate_real",
            [
                sys.executable,
                str(ROOT / "scripts" / "check_survivor_crash_falsification_gate_v1.py"),
                "--backtest-json",
                str(ART / "btrack_survivor_crash_correlation_backtest_real_latest.json"),
                "--output",
                str(gate_output_path),
                "--min-abs-corr",
                str(args.exploratory_min_abs_corr),
                "--max-pvalue",
                str(args.max_pvalue),
                "--min-n",
                str(args.min_n),
            ],
        ),
    ]

    for name, cmd in steps:
        runs[name] = _run(cmd)

    chain = _read_json(ART / "btrack_survivor_resonance_falsification_chain_latest.json")
    sweep = _read_json(ART / "btrack_survivor_crash_falsification_threshold_sweep_latest.json")
    gate_exploratory = _read_json(gate_output_path)
    tuning = _read_json(ART / "btrack_survivor_real_resonance_tuning_latest.json")

    out = {
        "schema": "survivor_resonance_operational_bundle_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "policy": {
            "default_exploratory_min_abs_corr": DEFAULT_EXPLORATORY_MIN_ABS_CORR,
            "validated_max_go_min_abs_corr": VALIDATED_MAX_GO_MIN_ABS_CORR,
            "current_exploratory_min_abs_corr": float(args.exploratory_min_abs_corr),
            "recommended_default": "conservative_default_0p08",
        },
        "inputs": {
            "exploratory_min_abs_corr": float(args.exploratory_min_abs_corr),
            "max_pvalue": float(args.max_pvalue),
            "min_n": int(args.min_n),
        },
        "runs": runs,
        "snapshots": {
            "chain_final_decision": ((chain.get("result") or {}).get("final_decision")),
            "exploratory_gate_decision": ((gate_exploratory.get("result") or {}).get("decision")),
            "exploratory_gate_output_path": str(gate_output_path),
            "tuning_best_weights": ((tuning.get("best") or {}).get("weights")),
            "sweep_rows": len(sweep.get("rows") or []),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    print(f"chain_final_decision={out['snapshots']['chain_final_decision']}")
    print(f"exploratory_gate_decision={out['snapshots']['exploratory_gate_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
