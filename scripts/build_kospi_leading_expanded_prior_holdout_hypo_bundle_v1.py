#!/usr/bin/env python3
"""[HYPO] Consolidate baseline vs expanded-prior lens WF + chronological holdout — research lane only."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/kospi_leading_expanded_prior_holdout_hypo_bundle_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _lens_mean(gates: dict[str, Any]) -> float | None:
    for gate in (gates.get("tracks") or {}).get("per_date_lens", {}).get("gates") or []:
        if gate.get("gate_id") == "lens_wf_mean_test_accuracy":
            v = (gate.get("observed") or {}).get("mean_test_accuracy")
            return float(v) if isinstance(v, (int, float)) else None
    return None


def _inst_mean(gates: dict[str, Any]) -> float | None:
    for gate in (gates.get("tracks") or {}).get("instrument_combo", {}).get("gates") or []:
        if gate.get("gate_id") == "instrument_wf_mean_test_accuracy":
            v = (gate.get("observed") or {}).get("mean_test_accuracy")
            return float(v) if isinstance(v, (int, float)) else None
    return None


def _fold_summary(wf: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in wf.get("folds") or []:
        if not isinstance(f, dict):
            continue
        test = f.get("test") if isinstance(f.get("test"), dict) else {}
        out.append(
            {
                "fold_index": f.get("fold_index"),
                "test_accuracy": test.get("accuracy"),
                "test_n": test.get("n"),
                "test_beats_always_bull": test.get("beats_always_bull"),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    baseline_gates = _load(ROOT / "reports/gates_leading_180d_v1_latest.json")
    expanded_gates = _load(ROOT / "reports/gates_leading_expanded_hypo_180d_v1_latest.json")
    holdout = _load(ROOT / "reports/lens_holdout_baseline_leading_180d_v1_latest.json")
    blind_holdout = _load(ROOT / "reports/lens_expanded_prior_blind_holdout_v1_latest.json")
    expanded_wf = _load(ROOT / "reports/lens_wf_leading_expanded_hypo_180d_btc_v1_latest.json")

    baseline_lens = _lens_mean(baseline_gates)
    expanded_lens = _lens_mean(expanded_gates)
    delta = round(expanded_lens - baseline_lens, 6) if baseline_lens is not None and expanded_lens is not None else None

    doc = {
        "schema": "kospi_leading_expanded_prior_holdout_hypo_bundle_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "ensemble_hypo_config": "reports/kospi_ensemble_hypo_leading_candidate_v1.json",
        "panel": {
            "score_json": "reports/btrack_score_leading_180d_v1_latest.json",
            "recent_trading_days": 180,
            "neutral_bps": 6,
            "kospi_in_sample_hit_rate_ovn050": 0.6722,
        },
        "lens_wf_btc": {
            "baseline": {
                "mean_test_accuracy": baseline_lens,
                "gates_json": "reports/gates_leading_180d_v1_latest.json",
                "per_date_lens_all_gates_passed": (baseline_gates.get("tracks") or {})
                .get("per_date_lens", {})
                .get("all_gates_passed"),
                "include_expanded_prior_features": False,
            },
            "expanded_prior_hypo": {
                "mean_test_accuracy": expanded_lens,
                "stdev_test_accuracy": (expanded_wf.get("aggregate") or {}).get("stdev_test_accuracy"),
                "min_test_accuracy": (expanded_wf.get("aggregate") or {}).get("min_test_accuracy"),
                "max_test_accuracy": (expanded_wf.get("aggregate") or {}).get("max_test_accuracy"),
                "fraction_test_beats_always_bull": (expanded_wf.get("aggregate") or {}).get(
                    "fraction_test_beats_always_bull"
                ),
                "include_source_direction_signal": True,
                "include_expanded_prior_features": True,
                "gates_json": "reports/gates_leading_expanded_hypo_180d_v1_latest.json",
                "walkforward_json": "reports/lens_wf_leading_expanded_hypo_180d_btc_v1_latest.json",
                "per_date_lens_all_gates_passed": (expanded_gates.get("tracks") or {})
                .get("per_date_lens", {})
                .get("all_gates_passed"),
                "fold_summary": _fold_summary(expanded_wf),
            },
            "delta_expanded_minus_baseline_mean": delta,
        },
        "instrument_wf": {
            "baseline_mean": _inst_mean(baseline_gates),
            "expanded_hypo_mean": _inst_mean(expanded_gates),
        },
        "chronological_holdout_baseline_lens_grid": {
            "artifact": "reports/lens_holdout_baseline_leading_180d_v1_latest.json",
            "note": "Legacy 7-param grid on dual-leg rows (kospi+btc); not BTC-only.",
            "train_accuracy": (holdout.get("train") or {}).get("accuracy"),
            "test_accuracy": (holdout.get("test") or {}).get("accuracy"),
            "test_beats_always_bull": holdout.get("test_beats_always_bull"),
            "test_always_bull_control": (holdout.get("test") or {}).get("always_bull_control"),
        },
        "blind_holdout_btc_single_split": {
            "artifact": "reports/lens_expanded_prior_blind_holdout_v1_latest.json",
            "note": "50/50 date split; BTC rows only; same grid family as walkforward.",
            "variants": {
                v.get("slug"): (v.get("test_blind") or {})
                for v in (blind_holdout.get("variants") or [])
                if isinstance(v, dict) and v.get("slug")
            },
            "delta_expanded_minus_baseline_blind_test": (blind_holdout.get("comparison") or {}).get(
                "delta_expanded_minus_baseline_blind_test_accuracy"
            ),
        },
        "promotion": {
            "baseline_combined_all_passed": baseline_gates.get("combined_all_passed"),
            "expanded_hypo_combined_all_passed": expanded_gates.get("combined_all_passed"),
            "track_a_blocked": True,
            "expanded_prior_promotion_axis": "forbidden_per_btrack_playbook",
            "operator_message": (
                "Expanded-prior lens WF may pass per_date_lens in isolation; "
                "do not merge into Track A or claim promotion from this lane alone."
            ),
        },
        "may_daily_flow": {
            "krx_credentials_set": False,
            "gaps_artifact": "reports/kospi_daily_flow_gaps_v1_latest.json",
            "may_2026_missing_n": 20,
            "status": "blocked_pending_krx_id_pw",
        },
        "instrument_wf_bottleneck": {
            "ablation_artifact": "reports/instrument_wf_bottleneck_ablation_v1_latest.json",
            "tuning_hypo": "reports/instrument_wf_hypo_tuning_leading_v1.json",
            "chain_default_mean": 0.546667,
            "recommended_fix": {
                "test_policy": "ensemble-top3",
                "n_folds": 6,
                "mean_test_accuracy": 0.576667,
            },
            "combined_with_baseline_lens_0_52": {
                "gates_json": "reports/gates_leading_baseline_lens_inst_ensemble_nf6_v1_latest.json",
                "combined_all_passed": False,
            },
            "combined_with_expanded_lens_hypo": {
                "gates_json": "reports/gates_leading_expanded_inst_ensemble_nf6_v1_latest.json",
                "combined_all_passed": True,
                "auto_promote_ready": False,
                "track_a_blocked": True,
                "expanded_prior_not_promotion_axis": True,
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"baseline_lens={baseline_lens} expanded_lens={expanded_lens} delta={delta}")
    print(f"combined baseline={doc['promotion']['baseline_combined_all_passed']} expanded={doc['promotion']['expanded_hypo_combined_all_passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
