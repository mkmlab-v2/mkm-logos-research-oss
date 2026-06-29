#!/usr/bin/env python3
"""[HYPO] Roll up NG-40 spine/billing-mode eval arms vs canonical frozen ACTIVE."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "reports/ng40_spine_billing_mode_rollup_v1_latest.json"

CANON_S = 0.47538677918424754
CANON_J = 0.8904921794966301

POINTERS = {
    "prior_diet_refine": (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_prior_residual_diet_refine_v1_latest.json"
    ),
    "prior_diet": (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_prior_residual_diet_v1_latest.json"
    ),
    "spine_binary": (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_spine_binary_billable_eval_v1_latest.json"
    ),
    "pareto_sweep": (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_commercialization_pareto_sweep_v1_latest.json"
    ),
    "hybrid_trilane": (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_hybrid_spine_trilane_stack_v1_latest.json"
    ),
    "latent_hybrid": "reports/ng40_latent_spine_hybrid_eval_v1_latest.json",
    "path_b_decomposition": "reports/ng40_path_b_dual_axis_beat_decomposition_v1_latest.json",
    "spine_binary_longform": (
        "experiments/nextgen_clean_slate_cpu_v1/results/"
        "ng40_spine_binary_billable_eval_longform_v1_latest.json"
    ),
    "longform_bench_input": (
        "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_LONGFORM_SPINE_BENCH_INPUT_V1.json"
    ),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    diet_ref = _load(POINTERS["prior_diet_refine"]) or _load(POINTERS["prior_diet"])
    spine_bin = _load(POINTERS["spine_binary"])
    spine_lf = _load(POINTERS["spine_binary_longform"])
    lf_bench = _load(POINTERS["longform_bench_input"])
    pareto = _load(POINTERS["pareto_sweep"])
    hybrid = _load(POINTERS["hybrid_trilane"])
    latent = _load(POINTERS["latent_hybrid"])
    path_b = _load(POINTERS["path_b_decomposition"])

    rec_zero = (diet_ref or {}).get("recommended_diet", {}).get("sidecar_zero_bill") or {}
    rec_bill = (diet_ref or {}).get("recommended_diet", {}).get("sidecar_billable") or {}
    spine_agg = (spine_bin or {}).get("aggregate") or {}
    spine_lf_agg = (spine_lf or {}).get("aggregate") or {}
    pareto_sum = (pareto or {}).get("pareto_summary") or {}
    lf_bytes = (lf_bench or {}).get("raw_utf8_bytes") or {}
    hybrid_agg = (hybrid or {}).get("aggregate") or {}

    billing_modes = [
        {
            "mode_id": "multilens_track_a_frozen",
            "lane": "Track A ACTIVE (canonical)",
            "byte_exact_parity": None,
            "billable_saving_rate": CANON_S,
            "jaccard_or_preview": CANON_J,
            "dual_axis_beat_vs_canon": True,
            "note": "Promotion gate reference only; not NG spine",
        },
        {
            "mode_id": "spine_json_only_zero_sidecar_bill",
            "lane": "verbatim spine JSON billable",
            "byte_exact_parity": rec_zero.get("byte_exact_subset_parity"),
            "billable_saving_rate": rec_zero.get("global_token_saving_rate_spine_json_only"),
            "jaccard_or_preview": rec_zero.get("avg_sidecar_preview_jaccard"),
            "dual_axis_beat_vs_canon": False,
            "keep_ratio": rec_zero.get("keep_ratio"),
        },
        {
            "mode_id": "spine_json_plus_sidecar_billable",
            "lane": "spine JSON + residual sidecar bytes",
            "byte_exact_parity": rec_bill.get("byte_exact_subset_parity"),
            "billable_saving_rate": rec_bill.get("global_token_saving_rate_billable_payload"),
            "jaccard_or_preview": rec_bill.get("avg_sidecar_preview_jaccard"),
            "dual_axis_beat_vs_canon": False,
            "keep_ratio": rec_bill.get("keep_ratio"),
        },
        {
            "mode_id": "spine_binary_mkvs_golden40",
            "lane": "MKVS binary billable · Golden-40 (short)",
            "bench_label": (spine_bin or {}).get("bench_label"),
            "case_count": spine_agg.get("case_count"),
            "byte_exact_parity": spine_agg.get("byte_exact_subset_parity"),
            "billable_saving_rate": spine_agg.get("global_token_saving_rate_spine_binary_billable"),
            "jaccard_or_preview": spine_agg.get("avg_reconstruction_fidelity_jaccard"),
            "dual_axis_beat_vs_canon": spine_agg.get("dual_axis_beat_binary_vs_frozen"),
        },
        {
            "mode_id": "spine_binary_mkvs_longform",
            "lane": "MKVS binary billable · long-form matrix (≥512B)",
            "bench_label": (spine_lf or {}).get("bench_label"),
            "case_count": spine_lf_agg.get("case_count"),
            "raw_utf8_bytes_avg": lf_bytes.get("avg"),
            "byte_exact_parity": spine_lf_agg.get("byte_exact_subset_parity"),
            "billable_saving_rate": spine_lf_agg.get("global_token_saving_rate_spine_binary_billable"),
            "jaccard_or_preview": spine_lf_agg.get("avg_reconstruction_fidelity_jaccard"),
            "dual_axis_beat_vs_canon": spine_lf_agg.get("dual_axis_beat_binary_vs_frozen"),
            "note": "Separate bench contract; not Golden-40; no Track A auto-merge",
        },
        {
            "mode_id": "hybrid_trilane_spine_plus_sidecar",
            "lane": "verbatim spine + trilane prior sidecar (NON_GATING)",
            "byte_exact_parity": hybrid_agg.get("byte_exact_subset_parity"),
            "billable_saving_rate": hybrid_agg.get(
                "global_token_saving_rate_spine_plus_trilane_sidecar"
            ),
            "jaccard_or_preview": hybrid_agg.get("avg_trilane_sidecar_jaccard"),
            "dual_axis_beat_vs_canon": False,
        },
    ]

    out = {
        "schema": "ng40_spine_billing_mode_rollup_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "canonical_frozen_active": {
            "global_token_saving_rate": CANON_S,
            "avg_reconstruction_fidelity_jaccard": CANON_J,
        },
        "billing_modes": billing_modes,
        "pareto_summary": {
            "grid_points": pareto_sum.get("grid_points"),
            "dual_axis_beat_count_legacy_json_plus_sidecar": pareto_sum.get(
                "dual_axis_beat_count_legacy_json_plus_sidecar"
            ),
            "dual_axis_beat_count_spine_json_only": pareto_sum.get(
                "dual_axis_beat_count_spine_json_only"
            ),
            "dual_axis_beat_count_spine_binary_mkvs": pareto_sum.get(
                "dual_axis_beat_count_spine_binary_mkvs"
            ),
            "best_payload_saving_rate": (pareto_sum.get("best_payload_saving_row") or {}).get(
                "payload_global_token_saving_rate"
            ),
        },
        "latent_path_b": {
            "any_latent_dual_axis_beat": (latent or {}).get("any_latent_dual_axis_beat"),
            "dual_axis_beat_count_canonical": (
                (path_b or {}).get("vs_canonical_frozen") or {}
            ).get("dual_axis_beat_count"),
        },
        "corpus_split_read_ko": (
            "Golden-40(짧문): spine JSON/MKVS 과금 payload가 Track A 대비 불리. "
            "Long-form(≥512B, 73건): MKVS binary만 byte_exact=1.0·saving beat 관측 — "
            "코퍼스·billing_mode 계약 분리 필수. latent Path-B(356 grid) dual-axis beat=0."
        ),
        "read_ko": (
            "상용 주장은 billing_mode·코퍼스별 SLA로만. "
            "longform MKVS beat는 Track A ACTIVE 승격 근거가 아님."
        ),
        "pointers": POINTERS,
        "promotion": {
            "apply_forbidden": True,
            "active_overwrite": False,
            "export_prep_ready": False,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "spine_dual_axis_modes": sum(
                    1 for m in billing_modes if m.get("dual_axis_beat_vs_canon")
                ),
                "pareto_dual_axis_total": sum(
                    int(pareto_sum.get(k) or 0)
                    for k in (
                        "dual_axis_beat_count_legacy_json_plus_sidecar",
                        "dual_axis_beat_count_spine_json_only",
                        "dual_axis_beat_count_spine_binary_mkvs",
                    )
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
