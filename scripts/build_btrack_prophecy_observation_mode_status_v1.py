#!/usr/bin/env python3
"""[HYPO] B-track prophecy observation-mode closure snapshot (no promote; ops SSOT)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_prophecy_observation_mode_status_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    alert1 = _load(ROOT / "reports/btrack_alert1_improvement_status_v1_latest.json") or {}
    advisory = _load(ROOT / "reports/btrack_advisory_bear_trap_manifest_v1_latest.json") or {}
    sweep = _load(ROOT / "reports/btrack_advisory_bear_trap_sweep_v1_latest.json") or {}
    train_pat = _load(ROOT / "reports/btrack_train_wrong_pattern_summary_v1_latest.json") or {}
    model_swap = _load(ROOT / "reports/btrack_model_swap_harness_v1_latest.json") or {}
    gate_candidate = _load(ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json") or {}
    aux_grid_180 = _load(ROOT / "reports/btrack_wrong_dir_auxiliary_grid_180d_v1_latest.json") or {}
    holdout_panel = _load(ROOT / "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json") or {}
    aux_closed = alert1.get("auxiliary_wrong_dir_holdout_closed") or {}

    prod = alert1.get("production_v1_min_conf_0.18") or {}
    report = {
        "schema": "btrack_prophecy_observation_mode_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "mode": "observation_ops_b",
        "ensemble_frozen": {
            "path": "docs/final/artifacts/btrack_lens_ensemble_v1.json",
            "min_direction_confidence": 0.18,
            "auto_promote": False,
        },
        "promotion_tracks_closed": {
            "auxiliary_wrong_dir": aux_closed.get("verdict_30d"),
            "choice2_lens_wf_retrain": "suspended",
            "alert_1_pass": prod.get("alert_1_pass"),
            "alert_1b_pass": prod.get("alert_1b_pass"),
        },
        "advisory_primary": {
            "rule": advisory.get("rule") or sweep.get("primary_rule"),
            "n_dates": advisory.get("n_dates"),
            "holdout7_wrong_overlap": advisory.get("holdout7_wrong_overlap") or [],
            "daily_refresh": (alert1.get("advisory_daily_refresh_v1") or {}).get("enabled"),
        },
        "train_wrong_pattern": {
            "holdout7_n": (train_pat.get("holdout_7_wrong_dir") or {}).get("n"),
            "train_wrong_n": (train_pat.get("train_wrong_dir") or {}).get("n"),
            "csv": train_pat.get("csv_path"),
            "gate_train_leakage_ok": (train_pat.get("holdout_gate_simulation") or {}).get(
                "train_leakage_ok"
            ),
        },
        "aux_grid_180d": {
            "best_holdout_neutralized_slug": (aux_grid_180.get("best_by_holdout_neutralized") or {}).get(
                "slug"
            ),
            "holdout_neutralized": (
                (aux_grid_180.get("best_by_holdout_neutralized") or {}).get("holdout_wrong_dir") or {}
            ).get("neutralized"),
            "verdict": aux_grid_180.get("verdict"),
        },
        "model_swap_poc": {
            "status": "closed",
            "verdict": model_swap.get("verdict"),
            "auto_promote": False,
            "gemini_oos_verdict": (
                _load(ROOT / "reports/btrack_gemini_per_date_oos_180d_v1_latest.json") or {}
            ).get("promotion", {}).get("verdict"),
            "path": "reports/btrack_model_swap_harness_v1_latest.json",
        },
        "holdout_gate_candidate": {
            "slug": (gate_candidate.get("candidate_layer") or {}).get("slug"),
            "holdout7_neutralized": (gate_candidate.get("holdout7") or {}).get(
                "n_holdout7_wrong_neutralized"
            ),
            "headline_30d_delta": (gate_candidate.get("metrics_30d") or {}).get("delta_headline"),
            "auto_promote": gate_candidate.get("deployment", {}).get("auto_promote"),
            "path": "reports/btrack_holdout_gate_candidate_v1_latest.json",
        },
        "holdout7_autopsy": {
            "gemini_same_trap_as_prod": (holdout_panel.get("summary") or {}).get(
                "gemini_avoids_prod_trap"
            )
            is False,
            "path": "reports/btrack_holdout7_gemini_vs_prod_panel_v1_latest.json",
        },
        "operator_lines": [],
    }
    rule = report["advisory_primary"].get("rule") or "unknown"
    n_adv = report["advisory_primary"].get("n_dates")
    h7 = report["advisory_primary"].get("holdout7_wrong_overlap") or []
    gc = report["holdout_gate_candidate"]
    gc_slug = gc.get("slug") or "holdout_ovn_signed_bull"
    gc_n = gc.get("holdout7_neutralized")
    gc_d = gc.get("headline_30d_delta")
    report["operator_lines"] = [
        "- [MKM-OBS-MODE] B-track prophecy: observation only; ensemble min_conf=0.18 frozen; no auto-promote.",
        f"- [MKM-OBS-MODE] Advisory primary={rule} n={n_adv} holdout7_wrong_hit={len(h7)}; daily advisory-sweep ON.",
        "- [MKM-OBS-MODE] Model swap PoC CLOSED (Gemini per-date); holdout7 7/7 same trap; no LLM promote.",
        f"- [MKM-OBS-MODE] Holdout gate candidate={gc_slug} holdout7_neutralized={gc_n}/7 "
        f"30d_delta={gc_d} research_only.",
        f"- [MKM-OBS-MODE] train_wrong n={(report['train_wrong_pattern'].get('train_wrong_n'))} "
        f"gate_train_leakage_ok={report['train_wrong_pattern'].get('gate_train_leakage_ok')}.",
        f"- [MKM-OBS-MODE] aux_grid_180 best_holdout_neutral="
        f"{report['aux_grid_180d'].get('best_holdout_neutralized_slug')} "
        f"{report['aux_grid_180d'].get('holdout_neutralized')}/7.",
        "- [MKM-OBS-MODE] Promotion tracks closed (aux/CBO/F2F3/Choice2); external result gate — panel log only.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
