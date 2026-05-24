#!/usr/bin/env python3
"""Fine-tune v2 lane: neutral_bps x per_date_min_confidence (B-track)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
OUT = ROOT / "reports/btrack_ensemble_v2_fine_tune_sweep_v1_latest.json"


def _gate_mean(gates: dict[str, Any], track: str, gid: str) -> float | None:
    for g in (gates.get("tracks") or {}).get(track, {}).get("gates") or []:
        if isinstance(g, dict) and g.get("gate_id") == gid:
            v = (g.get("observed") or {}).get("mean_test_accuracy")
            if isinstance(v, (int, float)):
                return float(v)
    return None


def main() -> int:
    rows: list[dict[str, Any]] = []
    best_pass: dict[str, Any] | None = None
    best_lex: tuple[float, float] | None = None
    best_row: dict[str, Any] | None = None

    nb_grid = [0.4, 0.5, 0.6, 0.8, 1.0, 1.25]
    conf_grid = [0.08, 0.1, 0.12, 0.15, 0.18, 0.2]

    for nb in nb_grid:
        for conf in conf_grid:
            slug = f"nb{str(nb).replace('.', 'p')}_c{str(conf).replace('.', 'p')}"
            gates_p = ROOT / "reports" / f"btrack_v2_ft_{slug}.json"
            cmd = [
                sys.executable,
                str(REC),
                "--recent-trading-days",
                "180",
                "--neutral-bps",
                str(nb),
                "--per-date-direction-json",
                str(DIRS),
                "--per-date-min-confidence",
                str(conf),
                "--include-source-direction-signal",
                "--include-expanded-prior-features",
                "--instrument-btc-policies",
                "prior,panel",
                "--instrument-include-panel-kospi-mode",
                "--gates-out",
                str(gates_p),
                "--score-json",
                str(ROOT / "reports" / f"btrack_v2_ft_sc_{slug}.json"),
                "--lens-walkforward-out",
                str(ROOT / "reports" / f"btrack_v2_ft_lens_{slug}.json"),
                "--instrument-walkforward-out",
                str(ROOT / "reports" / f"btrack_v2_ft_inst_{slug}.json"),
            ]
            rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
            gates: dict[str, Any] = {}
            if gates_p.is_file():
                gates = json.loads(gates_p.read_text(encoding="utf-8"))
            lm = _gate_mean(gates, "per_date_lens", "lens_wf_mean_test_accuracy")
            im = _gate_mean(gates, "instrument_combo", "instrument_wf_mean_test_accuracy")
            comb = bool(gates.get("combined_all_passed"))
            row = {
                "neutral_bps": nb,
                "per_date_min_confidence": conf,
                "exit_code": rc,
                "lens_mean": lm,
                "instrument_mean": im,
                "combined_all_passed": comb,
            }
            rows.append(row)
            tag = "PASS" if comb else "    "
            print(f"{tag} nb={nb} conf={conf} lens={lm} inst={im}", flush=True)
            if comb and best_pass is None:
                best_pass = row
            if lm is not None and im is not None:
                lex = (lm + im, min(lm, im))
                if best_lex is None or lex > best_lex:
                    best_lex = lex
                    best_row = row

    doc = {
        "schema": "btrack_ensemble_v2_fine_tune_sweep_v1",
        "rows": rows,
        "first_combined_all_passed": best_pass,
        "best_by_lex": best_row,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
