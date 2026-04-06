#!/usr/bin/env python3
"""Build a single benchmark bundle JSON for war-prolongation B-Track run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    gate_path = ART / "aidc_kpi_gate_war_20260406.json"
    perf_path = ART / "aidc_perf_ab_summary_war_20260406.json"
    hit_path = ART / "prophecy_hit_rate_eval_war_prolong_20260406_multileg.json"
    win_path = ART / "war_prolongation_window_eval_20260406.json"
    sig_path = ART / "war_prolongation_significance_eval_latest.json"
    score_path = ART / "btrack_prophecy_score_war_prolong_20260406_multileg.json"
    repro_path = ART / "repro_command_war_prolongation_20260406.txt"
    out_path = ART / "war_prolongation_benchmark_bundle_20260406.json"

    gate = _load(gate_path)
    perf = _load(perf_path)
    hit = _load(hit_path)
    win = _load(win_path)
    sig = _load(sig_path)

    decision = ((gate.get("go_no_go") or {}).get("decision")) or "NO_GO"
    reasons = ((gate.get("go_no_go") or {}).get("reasons")) or []
    perf_uplift = ((perf.get("uplift_perf_per_w_pct")))
    spot_hit = ((hit.get("metrics") or {}).get("price_directional_hit_rate")
    )
    h1 = (((win.get("summary_by_horizon") or {}).get("h1") or {}).get("hit_rate"))
    h5 = (((win.get("summary_by_horizon") or {}).get("h5") or {}).get("hit_rate"))
    h20 = (((win.get("summary_by_horizon") or {}).get("h20") or {}).get("hit_rate"))
    sig_n = (((sig.get("overall") or {}).get("n")))
    sig_p = (((sig.get("overall") or {}).get("p_value_one_sided_vs_baseline")))
    sig_ok = bool(((sig.get("overall") or {}).get("significant")))

    payload = {
        "schema": "war_prolongation_benchmark_bundle_v1",
        "generated_at_utc": _utc_now(),
        "run_id": "war_20260406",
        "lane": "btrack_observation_only",
        "inputs": {
            "score_json": str(score_path).replace("\\", "/"),
            "hit_eval_json": str(hit_path).replace("\\", "/"),
            "window_eval_json": str(win_path).replace("\\", "/"),
            "significance_eval_json": str(sig_path).replace("\\", "/"),
            "perf_ab_json": str(perf_path).replace("\\", "/"),
            "gate_json": str(gate_path).replace("\\", "/"),
            "repro_command": str(repro_path).replace("\\", "/"),
        },
        "snapshot": {
            "spot_hit_rate": spot_hit,
            "window_hit_rate_h1": h1,
            "window_hit_rate_h5": h5,
            "window_hit_rate_h20": h20,
            "significance_n": sig_n,
            "significance_p_value": sig_p,
            "significance_pass": sig_ok,
            "perf_per_w_uplift_pct": perf_uplift,
            "gate_decision": decision,
            "gate_reasons": reasons,
        },
        "promotion_recommendation": {
            "status": "HOLD" if decision != "GO" else "PROMOTE",
            "rationale": (
                "Hold in observation lane until gate turns GO with positive performance-per-watt uplift "
                "and statistically significant accuracy."
                if decision != "GO"
                else "Promotion eligible by gate."
            ),
        },
        "notes": [
            "Observation lane only. Not for live trading promotion.",
            "Window metrics currently use trailing_proxy fallback until forward bars accumulate.",
        ],
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

