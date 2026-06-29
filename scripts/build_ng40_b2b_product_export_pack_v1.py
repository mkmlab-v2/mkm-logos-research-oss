#!/usr/bin/env python3
"""[HYPO] Assemble B2B product export pack — spine official + sidecar; latent lane reference only."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT_JSON = ROOT / "reports/ng40_b2b_product_export_pack_v1_latest.json"
OUT_PASTE = ROOT / "reports/ng40_b2b_product_export_paste_v1_latest.txt"
CANONICAL_KEEP = 0.88


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _agg_metrics(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {}
    return doc.get("aggregate") or doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-paste", type=Path, default=OUT_PASTE)
    args = ap.parse_args()

    guarded = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
    )
    hybrid = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
    )
    trilane = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_trilane_stack_v1_latest.json"
    )
    bundle = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_b2b_design_bundle_v1_latest.json"
    )
    latent = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_trilane_prior_41k_v1_latest.json"
    )

    g_agg = _agg_metrics(guarded)
    h_agg = _agg_metrics(hybrid)
    t_agg = _agg_metrics(trilane)
    contract_met = bool(
        g_agg.get("contract_met")
        or (guarded or {}).get("contract_met")
        or ((bundle or {}).get("guarded_b2b") or {}).get("contract_met")
    )
    byte_p = float(
        g_agg.get("byte_exact_subset_parity")
        or (guarded or {}).get("byte_exact_subset_parity")
        or ((bundle or {}).get("guarded_b2b") or {}).get("byte_exact_subset_parity")
        or h_agg.get("byte_exact_subset_parity")
        or 0
    )
    product_ready = contract_met and byte_p >= 1.0

    frozen = {"present": False}
    if ACTIVE.is_file():
        cm = json.loads(ACTIVE.read_text(encoding="utf-8-sig")).get("compression_metrics") or {}
        frozen = {
            "present": True,
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        }

    latent_agg = (latent or {}).get("aggregate") or {}
    latent_beat = (latent or {}).get("beat_check") or {}

    pack = {
        "schema": "ng40_b2b_product_export_pack_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "product_lane": {
            "definition_ko": "공식 B2B 복원 = verbatim spine only; sidecar = preview/metrics",
            "canonical_keep_ratio": CANONICAL_KEEP,
            "byte_exact_subset_parity": byte_p,
            "guarded_contract_met": contract_met,
            "product_ready": product_ready,
            "pointers": {
                "guarded_b2b": (
                    "experiments/nextgen_clean_slate_cpu_v1/results/"
                    "ng40_guarded_b2b_decode_contract_v1_latest.json"
                ),
                "hybrid_logos_stack": (
                    "experiments/nextgen_clean_slate_cpu_v1/results/"
                    "ng40_hybrid_spine_logos_stack_v1_latest.json"
                ),
                "hybrid_trilane_stack": (
                    "experiments/nextgen_clean_slate_cpu_v1/results/"
                    "ng40_hybrid_spine_trilane_stack_v1_latest.json"
                ),
                "design_bundle": (
                    "experiments/nextgen_clean_slate_cpu_v1/results/"
                    "ng40_hybrid_b2b_design_bundle_v1_latest.json"
                ),
            },
            "metrics": {
                "hybrid_logos_byte_exact": h_agg.get("byte_exact_subset_parity"),
                "hybrid_logos_sidecar_jaccard": h_agg.get(
                    "avg_reconstruction_fidelity_jaccard"
                ),
                "trilane_byte_exact": t_agg.get("byte_exact_subset_parity"),
                "trilane_sidecar_jaccard": t_agg.get("avg_reconstruction_fidelity_jaccard"),
            },
        },
        "research_lane_reference": {
            "role_ko": "latent Golden-40 eval — B2B 헤드라인·청구·ACTIVE 교체 근거로 사용 금지",
            "arm_id": (latent or {}).get("arm_id"),
            "prior_terms_count": (latent or {}).get("prior_terms_count"),
            "saving": latent_agg.get("global_token_saving_rate"),
            "jaccard": latent_agg.get("avg_reconstruction_fidelity_jaccard"),
            "beat_frozen_active": latent_beat.get("beat_frozen"),
            "pointer": (
                "experiments/nextgen_clean_slate_cpu_v1/results/"
                "ng40_latent_eval_path_b_trilane_prior_41k_v1_latest.json"
            ),
        },
        "frozen_active_reference": frozen,
        "reporting": {
            "raw_primary_product": True,
            "latent_not_collapsed_into_product_headline": True,
        },
        "forbidden": [
            "use latent saving/jaccard as B2B SLA or ACTIVE apply headline",
            "merge research_lane into product_lane billing",
            "--apply-active",
        ],
    }

    paste_lines = [
        "[HYPO] NG-40 B2B product export (internal) — research_only",
        "",
        "■ Product lane (billable official recon)",
        f"  keep_ratio: {CANONICAL_KEEP}",
        f"  byte_exact_subset_parity: {byte_p}",
        f"  guarded_contract_met: {contract_met}",
        f"  product_ready: {product_ready}",
        "",
        "■ Research lane reference ONLY (do not paste to MS / Track A headline)",
        f"  arm: {(latent or {}).get('arm_id', 'n/a')}",
        f"  saving: {latent_agg.get('global_token_saving_rate')}",
        f"  jaccard: {latent_agg.get('avg_reconstruction_fidelity_jaccard')}",
        f"  beat_frozen ACTIVE: {latent_beat.get('beat_frozen')}",
        "",
        "■ Frozen ACTIVE (reference)",
        f"  saving: {frozen.get('global_token_saving_rate')}",
        f"  jaccard: {frozen.get('avg_reconstruction_fidelity_jaccard')}",
        "",
        f"JSON: {args.out_json.relative_to(ROOT).as_posix()}",
    ]

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.out_paste.write_text("\n".join(paste_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote_json": str(args.out_json),
                "wrote_paste": str(args.out_paste),
                "product_ready": product_ready,
            },
            ensure_ascii=False,
        )
    )
    return 0 if product_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
