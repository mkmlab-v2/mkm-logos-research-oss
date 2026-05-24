#!/usr/bin/env python3
"""Tune instrument WF (decoupled leg + beat-bull train weight) for v2 lane combined pass."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
OUT = ROOT / "reports/btrack_ensemble_v2_inst_tune_sweep_v1_latest.json"


def _obs(g: dict, track: str, gid: str):
    for x in (g.get("tracks") or {}).get(track, {}).get("gates") or []:
        if x.get("gate_id") == gid:
            return x.get("observed") or {}
    return {}


def main() -> int:
    rows = []
    first = None
    for decoupled in (True, False):
        for bbw in [0.0, 0.02, 0.03, 0.05, 0.08]:
            if not decoupled and bbw > 0:
                continue
            slug = f"d{1 if decoupled else 0}_bb{str(bbw).replace('.', 'p')}"
            gates_p = ROOT / "reports" / f"v2_tune_{slug}.json"
            cmd = [
                sys.executable,
                str(REC),
                "--recent-trading-days",
                "180",
                "--neutral-bps",
                "0.8",
                "--per-date-direction-json",
                str(DIRS),
                "--per-date-min-confidence",
                "0.08",
                "--include-source-direction-signal",
                "--include-expanded-prior-features",
                "--instrument-btc-policies",
                "panel",
                "--instrument-include-panel-kospi-mode",
                "--gates-out",
                str(gates_p),
                "--score-json",
                str(ROOT / "reports" / f"v2_tune_sc_{slug}.json"),
                "--lens-walkforward-out",
                str(ROOT / "reports" / f"v2_tune_lens_{slug}.json"),
                "--instrument-walkforward-out",
                str(ROOT / "reports" / f"v2_tune_inst_{slug}.json"),
            ]
            # beat-bull weight CLI is accepted by recommended_eval_chain for compatibility only;
            # instrument WF is driven by score panel + instrument_combo_walkforward.
            if bbw > 0:
                cmd.extend(["--instrument-beat-bull-train-weight", str(bbw)])
            rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
            g = json.loads(gates_p.read_text(encoding="utf-8")) if gates_p.is_file() else {}
            lm = _obs(g, "per_date_lens", "lens_wf_mean_test_accuracy").get("mean_test_accuracy")
            im = _obs(g, "instrument_combo", "instrument_wf_mean_test_accuracy").get("mean_test_accuracy")
            bull = _obs(g, "instrument_combo", "instrument_wf_fraction_folds_beat_always_bull").get(
                "fraction_test_beats_always_bull"
            )
            comb = bool(g.get("combined_all_passed"))
            row = {
                "decoupled_leg_fit": decoupled,
                "beat_bull_train_weight": bbw,
                "rc": rc,
                "lens_mean": lm,
                "inst_mean": im,
                "inst_beat_bull_frac": bull,
                "combined_all_passed": comb,
            }
            rows.append(row)
            mark = "PASS" if comb else "   "
            print(f"{mark} dec={decoupled} bbw={bbw} lens={lm} inst={im} bull={bull}", flush=True)
            if comb and first is None:
                first = row
    OUT.write_text(json.dumps({"rows": rows, "first_combined_all_passed": first}, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
