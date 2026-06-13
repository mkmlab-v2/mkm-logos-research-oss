#!/usr/bin/env python3
"""Consolidate P0 B-layer experiment run results into one SSOT artifact [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/p0_role_contract_experiment_results_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _myeongni_summary(doc: dict[str, Any], window: int) -> dict[str, Any]:
    g = doc.get("myeongni_horizon_grid") if isinstance(doc.get("myeongni_horizon_grid"), dict) else {}
    return {
        "momentum_window": window,
        "n_eval_dates": g.get("n_eval_dates"),
        "contract_horizon": g.get("contract_horizon"),
        "contract_soft_hit_rate": g.get("contract_soft_hit_rate"),
        "best_horizon": g.get("best_horizon"),
        "best_soft_hit_rate": g.get("best_soft_hit_rate"),
        "contract_is_best": g.get("contract_is_best"),
    }


def build(*, root: Path) -> dict[str, Any]:
    horizon = _load(root / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json")
    logos_eval = horizon.get("logos_per_date_eval") if isinstance(horizon.get("logos_per_date_eval"), dict) else {}
    cov = logos_eval.get("macro_risk_coverage") if isinstance(logos_eval.get("macro_risk_coverage"), dict) else {}

    join_meta = _load(root / "reports/btrack_session_panel_wide_full_window_v1.join.meta.json")
    join_counts = join_meta.get("counts") if isinstance(join_meta.get("counts"), dict) else {}
    weather_hits = join_counts.get("n_rows_with_any_weather_cell_nonblank")

    corr_doc = _load(root / "reports/btrack_joined_wide_correlation_full_window_v1.json")
    top_wthr = sorted(
        [
            {
                "x_col": c.get("x_col"),
                "pearson_r": c.get("pearson_r"),
                "n_pairs": c.get("n_pairs"),
            }
            for c in (corr_doc.get("correlations") or [])
            if isinstance(c, dict)
            and str(c.get("x_col", "")).startswith("wthr_")
            and c.get("status") == "computed"
            and isinstance(c.get("pearson_r"), (int, float))
        ],
        key=lambda x: abs(float(x["pearson_r"])),
        reverse=True,
    )[:3]

    intensity_sweep = []
    for label, path in (
        ("h3", root / "reports/three_lens_horizon_intensity_h3_v1.json"),
        ("h5", horizon),
        ("h7", root / "reports/three_lens_horizon_intensity_h7_v1.json"),
    ):
        doc_i = _load(path) if label != "h5" else horizon
        ie = doc_i.get("sasang_intensity_eval") if isinstance(doc_i.get("sasang_intensity_eval"), dict) else {}
        intensity_sweep.append(
            {
                "horizon_days": ie.get("intensity_horizon_days") or label,
                "spearman_rank_corr": ie.get("spearman_rank_corr"),
                "intensity_pass": ie.get("intensity_pass"),
                "mechanical_proxy_suspect": float(ie.get("spearman_rank_corr") or 0) > 0.99,
            }
        )

    pack_watch_path = root / "reports/pack0b_full500_ordered_watch_latest.json"
    pack_watch = _load(pack_watch_path) if pack_watch_path.is_file() else {}
    pack_phase = str(pack_watch.get("phase") or "")
    if pack_phase == "training":
        pack_status = "training"
        pack_note = (
            f"full500 step {pack_watch.get('last_step')}/500 "
            f"ckpt={pack_watch.get('resume_checkpoint')}"
        )
    elif pack_phase == "done":
        pack_status = "completed"
        pack_note = "Run-Pack0bOrderedTrain full500 + locked_eval done"
    elif pack_phase == "failed":
        pack_status = "failed"
        pack_note = "Run-Pack0bOrderedTrain full500 failed — see pack0b_ordered_train_v1.log"
    elif (root / "reports/pack0b_ordered_train_v1.lock").is_file():
        pack_status = "lock_present"
        pack_note = "Run-Pack0bOrderedTrain lock present — verify train pid"
    else:
        pack_status = "no_lock"
        pack_note = "Pack0-B ordered train idle — not restarted this turn"

    fusion_doc = _load(root / "reports/myeongni_full_window_disaster_risk_fusion_v1_latest.json")
    fusion_sum = fusion_doc.get("summary") if isinstance(fusion_doc.get("summary"), dict) else {}

    return {
        "schema": "p0_role_contract_experiment_results_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "RESEARCH_ONLY_HYPO_B",
        "experiments": {
            "exp_logos_causal_macro_path_v1": {
                "status": "partial_pass",
                "actions_taken": [
                    "Removed --no-logos-jsonl from Invoke-LensSovereigntyAudit_v1.ps1",
                    "Re-ran horizon eval with logos_per_date jsonl write",
                    "Restored KOSPI CSV 7260 rows (1996-2026) after transient truncation",
                ],
                "results": {
                    "logos_per_date_jsonl": horizon.get("logos_per_date_jsonl"),
                    "n_eval_dates": horizon.get("v1_direction_eval", {}).get("n_eval_dates"),
                    "best_variant_by_macro_soft": logos_eval.get("best_variant_by_macro_soft"),
                    "operational_causal_rate": cov.get("operational_causal_rate"),
                    "research_backfill_rate": cov.get("research_backfill_rate"),
                    "variants_macro_alignment_pass_effective": logos_eval.get(
                        "variants_macro_alignment_pass_effective"
                    ),
                },
                "pass_criterion_met": False,
                "blocker": "operational_causal_rate still ~0.0011 (< 0.05 gate)",
            },
            "exp_myeongni_direction_signal_v1": {
                "status": "fail_flat_grid",
                "actions_taken": [
                    "Momentum window sweep 5/10/15 on full 7235 eval dates",
                    "30y weather fetch (10769 rows) + join 7693/7693 + full-window correlation",
                    "Chain y-col fix ohlcv_Close",
                ],
                "myeongni_momentum_sweep": [
                    _myeongni_summary(horizon, 5),
                    _myeongni_summary(_load(root / "reports/three_lens_horizon_momentum10_v1.json"), 10),
                    _myeongni_summary(_load(root / "reports/three_lens_horizon_momentum15_v1.json"), 15),
                ],
                "weather_corr_chain": {
                    "tag": "full_window_v1",
                    "date_from": "1996-12-11",
                    "date_to": "2026-06-05",
                    "weather_csv_rows": 10769,
                    "join_weather_hits": weather_hits,
                    "correlation_json": "reports/btrack_joined_wide_correlation_full_window_v1.json",
                    "top_weather_pearson_vs_close": top_wthr,
                    "status": "completed" if weather_hits and int(weather_hits) > 1000 else "partial",
                },
                "full_window_disaster_risk_fusion": {
                    "report_json": "reports/myeongni_full_window_disaster_risk_fusion_v1_latest.json",
                    "n_days": fusion_sum.get("n_days"),
                    "grade_changes": fusion_sum.get("grade_changes"),
                    "wide_csv": "reports/myeongni_full_window_fusion_wide_v1.csv",
                    "status": "completed" if fusion_sum.get("n_days") else "missing",
                },
                "pack0b_lora": {
                    "status": pack_status,
                    "note": pack_note,
                    "watch_json": "reports/pack0b_full500_ordered_watch_latest.json",
                },
                "pass_criterion_met": False,
                "blocker": "All momentum windows ~50% soft_hit — independent direction signal absent",
            },
            "exp_sasang_intensity_proxy_audit_v1": {
                "status": "mechanical_proxy_confirmed",
                "intensity_horizon_sweep": intensity_sweep,
                "note": "Spearman ~0.9998 at h3/h5/h7 — leakage/proxy duplication; pass gate not promotion-grade",
            },
        },
        "promotion_ready": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()
    root = ns.workspace_root.resolve()
    doc = build(root=root)
    out = ns.out_json if ns.out_json.is_absolute() else root / ns.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
