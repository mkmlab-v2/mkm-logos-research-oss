#!/usr/bin/env python3
"""[HYPO] One-shot: blind-window session JSONL → sidecar → OOS → blind/confirm holdout."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json"
MY = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.sparse_blind_session_fill_v1.jsonl"
SA = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.sparse_blind_session_fill_v1.jsonl"
SIDECAR = ROOT / "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_30y_sparse_blind_session_fill_v1.json"
OOS_OUT = ROOT / "reports/logos_oos_kospi_sparse_blind_session_fill_v1_latest.json"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-jsonl", action="store_true")
    args = ap.parse_args()

    if not args.skip_jsonl:
        _run([PY, str(ROOT / "scripts/build_myeongni_jsonl_blind_window_session_fill_v1.py")])
    _run(
        [
            PY,
            str(ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"),
            "--score-json",
            str(SCORE),
            "--out",
            str(SIDECAR),
            "--myeongni-experiment-jsonl",
            str(MY),
            "--sasang-dynamics-jsonl",
            str(SA),
            "--skip-external-observations",
        ]
    )
    _run(
        [
            PY,
            str(ROOT / "scripts/run_prophecy_lens_role_router_oos_gate_v1.py"),
            "--target-instrument",
            "kospi",
            "--score-json",
            str(SCORE),
            "--sidecar-json",
            str(SIDECAR),
            "--month-lookback-grid",
            "28",
            "--neutral-size-grid",
            "0.15",
            "--oos-tail-days",
            "252",
            "--gate-min-hit-rate",
            "0.52",
            "--output",
            str(OOS_OUT),
        ]
    )
    _run([PY, str(ROOT / "scripts/run_logos_oos_blind_holdout_fixed_dates_v1.py")])
    print("DONE: compare with golden via compare_logos_oos_sidecar_variants_v1.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
