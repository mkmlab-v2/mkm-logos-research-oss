#!/usr/bin/env python3
"""Sweep nbps x conf with instrument panel-only until combined strict passes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
OUT = ROOT / "reports/btrack_ensemble_v2_panel_inst_sweep_v1_latest.json"

NB_GRID = [0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5]
CONF_GRID = [0.0, 0.05, 0.08, 0.1, 0.12, 0.15]


def _obs(g: dict, track: str, gid: str) -> dict:
    for x in (g.get("tracks") or {}).get(track, {}).get("gates") or []:
        if x.get("gate_id") == gid:
            return x.get("observed") or {}
    return {}


def _pair_key(nb: float, conf: float) -> tuple[float, float]:
    return (float(nb), float(conf))


def _load_existing() -> tuple[list[dict], dict | None]:
    if not OUT.is_file():
        return [], None
    try:
        doc = json.loads(OUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], None
    rows = list(doc.get("rows") or [])
    first = doc.get("first_combined_all_passed")
    return rows, first if isinstance(first, dict) else None


def _write_progress(rows: list[dict], first: dict | None) -> None:
    doc = {
        "rows": rows,
        "first_combined_all_passed": first,
        "grid_complete": len(rows) >= len(NB_GRID) * len(CONF_GRID),
        "n_rows": len(rows),
        "n_expected": len(NB_GRID) * len(CONF_GRID),
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing OUT rows and rerun all grid cells.",
    )
    ap.add_argument(
        "--verbose-chain",
        action="store_true",
        help="Print recommended_eval_chain stdout/stderr (default: quiet).",
    )
    args = ap.parse_args()

    rows: list[dict] = []
    first: dict | None = None
    done: set[tuple[float, float]] = set()
    if not args.no_resume:
        rows, first = _load_existing()
        for r in rows:
            done.add(_pair_key(r["neutral_bps"], r["per_date_min_confidence"]))

    capture = None if args.verbose_chain else subprocess.DEVNULL

    for nb in NB_GRID:
        for conf in CONF_GRID:
            key = _pair_key(nb, conf)
            if key in done:
                print(f"skip nb={nb} c={conf} (resume)", flush=True)
                continue
            slug = f"nb{str(nb).replace('.', 'p')}_c{str(conf).replace('.', 'p')}"
            gates_p = ROOT / "reports" / f"v2_panel_{slug}.json"
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
                "panel",
                "--instrument-include-panel-kospi-mode",
                "--gates-out",
                str(gates_p),
                "--score-json",
                str(ROOT / "reports" / f"v2_panel_sc_{slug}.json"),
                "--lens-walkforward-out",
                str(ROOT / "reports" / f"v2_panel_lens_{slug}.json"),
                "--instrument-walkforward-out",
                str(ROOT / "reports" / f"v2_panel_inst_{slug}.json"),
            ]
            rc = subprocess.run(cmd, cwd=str(ROOT), stdout=capture, stderr=capture).returncode
            g = json.loads(gates_p.read_text(encoding="utf-8")) if gates_p.is_file() else {}
            lm = _obs(g, "per_date_lens", "lens_wf_mean_test_accuracy").get("mean_test_accuracy")
            im = _obs(g, "instrument_combo", "instrument_wf_mean_test_accuracy").get("mean_test_accuracy")
            bull = _obs(g, "instrument_combo", "instrument_wf_fraction_folds_beat_always_bull").get(
                "fraction_test_beats_always_bull"
            )
            comb = bool(g.get("combined_all_passed"))
            row = {
                "neutral_bps": nb,
                "per_date_min_confidence": conf,
                "rc": rc,
                "lens_mean": lm,
                "inst_mean": im,
                "inst_beat_bull_frac": bull,
                "combined_all_passed": comb,
            }
            rows.append(row)
            done.add(key)
            _write_progress(rows, first)
            mark = "PASS" if comb else "   "
            print(f"{mark} nb={nb} c={conf} rc={rc} lens={lm} inst={im} bull_frac={bull}", flush=True)
            if comb and first is None:
                first = row
                _write_progress(rows, first)

    _write_progress(rows, first)
    print(f"WROTE {OUT} grid_complete={len(rows) >= len(NB_GRID) * len(CONF_GRID)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
