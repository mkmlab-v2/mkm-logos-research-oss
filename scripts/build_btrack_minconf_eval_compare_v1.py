#!/usr/bin/env python3
"""Compare v2 eval WF: baseline directions vs min_conf 0.25 gated directions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REC_CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
REPORTS = ROOT / "reports"
BASELINE_DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
GATED_025 = ROOT / "reports/btrack_per_date_min_conf_sweep_v1/directions_minconf_0p25.json"
OUT = ROOT / "reports/btrack_minconf_025_eval_compare_v1_latest.json"
GATES_BASE = ROOT / "reports/prophecy_promotion_gates_ensemble_v2_lane_baseline_compare.json"
GATES_GATED = ROOT / "reports/prophecy_promotion_gates_ensemble_v2_lane_minconf_025.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gate_mean(gates: dict[str, Any], track: str, gid: str) -> float | None:
    for g in (gates.get("tracks") or {}).get(track, {}).get("gates") or []:
        if isinstance(g, dict) and g.get("gate_id") == gid:
            v = (g.get("observed") or {}).get("mean_test_accuracy")
            if isinstance(v, (int, float)):
                return float(v)
    return None


def _run_eval(*, per_date_json: Path, gates_out: Path, summary_out: Path) -> tuple[int, dict[str, Any]]:
    """Recommended chain only — avoids eval_chain rebuilding per-date dirs over gated input."""
    cmd = [
        sys.executable,
        str(REC_CHAIN),
        "--recent-trading-days",
        "180",
        "--neutral-bps",
        "1.5",
        "--n-folds",
        "5",
        "--score-json",
        str(REPORTS / "btrack_prophecy_score_ensemble_v2_lane_v1_latest.json"),
        "--lens-walkforward-out",
        str(REPORTS / "prophecy_per_date_combo_walkforward_minconf_compare_v1_latest.json"),
        "--instrument-walkforward-out",
        str(REPORTS / "prophecy_instrument_combo_walkforward_minconf_compare_v1_latest.json"),
        "--gates-out",
        str(gates_out),
        "--summary-out",
        str(summary_out),
        "--per-date-direction-json",
        str(per_date_json),
        "--include-source-direction-signal",
        "--include-expanded-prior-features",
        "--instrument-btc-policies",
        "prior,panel",
        "--per-date-min-confidence",
        "0.08",
        "--calibration-note",
        f"minconf_compare per_date={per_date_json.name}",
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    gates = json.loads(gates_out.read_text(encoding="utf-8")) if gates_out.is_file() else {}
    return rc, gates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    if not BASELINE_DIRS.is_file():
        print(f"Missing {BASELINE_DIRS}", file=sys.stderr)
        return 2
    if not GATED_025.is_file():
        print(f"Missing {GATED_025}; run run_btrack_per_date_min_conf_sweep_v1.py first", file=sys.stderr)
        return 2

    rc_b, gates_b = _run_eval(
        per_date_json=BASELINE_DIRS,
        gates_out=GATES_BASE,
        summary_out=REPORTS / "btrack_minconf_compare_baseline_summary_v1_latest.json",
    )
    rc_g, gates_g = _run_eval(
        per_date_json=GATED_025,
        gates_out=GATES_GATED,
        summary_out=REPORTS / "btrack_minconf_compare_gated_025_summary_v1_latest.json",
    )

    def _pack(gates: dict[str, Any]) -> dict[str, Any]:
        return {
            "lens_mean": _gate_mean(gates, "per_date_lens", "lens_wf_mean_test_accuracy"),
            "instrument_mean": _gate_mean(gates, "instrument_combo", "instrument_wf_mean_test_accuracy"),
            "combined_all_passed": bool(gates.get("combined_all_passed")),
            "outcome_class": gates.get("outcome_class"),
        }

    pb, pg = _pack(gates_b), _pack(gates_g)
    doc = {
        "schema": "btrack_minconf_025_eval_compare_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "baseline": {"per_date_json": str(BASELINE_DIRS), "exit_code": rc_b, **pb},
        "min_conf_0_25_gated": {"per_date_json": str(GATED_025), "exit_code": rc_g, **pg},
        "delta": {
            "lens_mean_pp": round((float(pg["lens_mean"] or 0) - float(pb["lens_mean"] or 0)) * 100, 3)
            if pg.get("lens_mean") is not None and pb.get("lens_mean") is not None
            else None,
            "instrument_mean_pp": round(
                (float(pg["instrument_mean"] or 0) - float(pb["instrument_mean"] or 0)) * 100, 3
            )
            if pg.get("instrument_mean") is not None and pb.get("instrument_mean") is not None
            else None,
        },
        "note": "Uses recommended eval chain with fixed --per-date-direction-json (no v2 dir rebuild).",
    }
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    print(
        f"baseline lens={pb.get('lens_mean')} inst={pb.get('instrument_mean')} | "
        f"gated lens={pg.get('lens_mean')} inst={pg.get('instrument_mean')}",
        file=sys.stderr,
    )
    return 0 if rc_b == 0 and rc_g == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
