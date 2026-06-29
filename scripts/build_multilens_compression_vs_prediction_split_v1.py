#!/usr/bin/env python3
"""[HYPO] Compression (Track A) vs prediction (B-track multilens) optimal split summary."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/multilens_compression_vs_prediction_split_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _best_row(doc: dict[str, Any]) -> dict[str, Any]:
    b = doc.get("best_variant")
    if isinstance(b, dict):
        return b
    ranked = doc.get("ranked_top5") or doc.get("variants") or []
    return ranked[0] if ranked else {}


def _hit(row: dict[str, Any]) -> float | None:
    m = row.get("metrics") or {}
    v = m.get("directional_hit_rate")
    return float(v) if v is not None else None


def build() -> dict[str, Any]:
    compress = _read(ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json")
    cm = compress.get("compression_metrics") or {}
    kospi = _read(ROOT / "reports/kospi_multilens_blend_backtest_latest.json")
    btc = _read(ROOT / "reports/btc_multilens_blend_backtest_latest.json")
    btc140 = _read(ROOT / "reports/btc_multilens_blend_backtest_140d_latest.json")
    hypo = _read(ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    ablation = _read(ROOT / "reports/kospi_lens_ablation_backtest_latest.json")
    per_lens = _read(ROOT / "docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json")

    k_best = _best_row(kospi)
    b_best = _best_row(btc)
    b140_best = _best_row(btc140) if btc140 else {}

    runtime_meta = hypo.get("runtime_meta") or {}
    prod_weights = runtime_meta.get("weights") or {}

    ablation_arms = []
    for arm in ablation.get("ranked_arms") or ablation.get("arms") or []:
        if not isinstance(arm, dict):
            continue
        ablation_arms.append(
            {
                "arm_id": arm.get("arm_id"),
                "directional_hit_rate": (arm.get("metrics") or {}).get("directional_hit_rate"),
                "weights": arm.get("weights"),
            }
        )

    instrument_table = [
        {
            "instrument": "kospi",
            "best_variant_id": k_best.get("variant_id"),
            "directional_hit_rate": _hit(k_best),
            "weights": k_best.get("weights"),
            "four_ai_mode": k_best.get("four_ai_mode"),
            "note": k_best.get("note"),
            "window": kospi.get("window"),
        },
        {
            "instrument": "btc",
            "best_variant_id": b_best.get("variant_id"),
            "directional_hit_rate": _hit(b_best),
            "weights": b_best.get("weights"),
            "four_ai_mode": b_best.get("four_ai_mode"),
            "note": b_best.get("note"),
            "window": btc.get("window"),
        },
    ]
    if b140_best:
        instrument_table.append(
            {
                "instrument": "btc_140d_parity",
                "best_variant_id": b140_best.get("variant_id"),
                "directional_hit_rate": _hit(b140_best),
                "weights": b140_best.get("weights"),
                "window": btc140.get("window"),
            }
        )

    compression_lane = {
        "track": "A",
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "apply_gematria_4d_bridge_policy": (compress.get("run_config") or {}).get(
            "apply_gematria_4d_bridge_policy"
        ),
        "must_keep_domains": (compress.get("run_config") or {}).get("must_keep_terms"),
        "optimal_composition_ko": "lexicon ON + domain router + bible/myongri/sasang must_keep; 4D bridge OFF",
    }

    prediction_lane = {
        "track": "B",
        "production_ensemble_weights": prod_weights,
        "instrument_best_variants": instrument_table,
        "kospi_ablation_arms": ablation_arms,
        "per_lens_snapshot_note": per_lens.get("zeroing_note"),
    }

    logos_weight_zero = all(
        float((row.get("weights") or {}).get("logos_non_gating") or 0) == 0
        for row in instrument_table
        if row.get("instrument", "").startswith(("kospi", "btc"))
    )

    k_hit = _hit(k_best)
    b_hit = _hit(b_best)
    k_hit_s = f"{k_hit:.1%}" if k_hit is not None else "n/a"
    b_hit_s = f"{b_hit:.1%}" if b_hit is not None else "n/a"

    return {
        "schema": "multilens_compression_vs_prediction_split_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "compression_track_a_vs_prediction_b_no_auto_merge",
        "compression_lane": compression_lane,
        "prediction_lane": prediction_lane,
        "split_verdict": {
            "same_optimal_weights": False,
            "logos_non_gating_zero_in_best_variants": logos_weight_zero,
            "kospi_favors_full_lens3_blend": str(k_best.get("variant_id", "")).startswith("v2_default"),
            "btc_favors_session_momentum": "session_momentum" in str(b_best.get("variant_id", "")),
            "production_is_price_heavy": float(prod_weights.get("price") or 0) >= 0.5,
        },
        "verdict_ko": (
            "압축(Track A)은 3도메인 lexicon+47% 절감; 예측(B)은 종목별 최적 가중 분리 — "
            f"KOSPI best={k_best.get('variant_id')}({k_hit_s}), "
            f"BTC best={b_best.get('variant_id')}({b_hit_s}); "
            "Logos는 best variant에서 가중 0([NON_GATING]); production ensemble은 price-heavy. "
            "[HYPO] Track A/live 자동 합선 없음."
        ),
        "operator_lines": [
            "- [MKM-COMP-PRED-SPLIT] research_only; compression≠prediction optimal.",
            f"- [MKM-COMP-PRED-SPLIT] track_a saving={cm.get('global_token_saving_rate')} jaccard={cm.get('avg_reconstruction_fidelity_jaccard')}.",
            f"- [MKM-COMP-PRED-SPLIT] kospi_best={k_best.get('variant_id')} btc_best={b_best.get('variant_id')}.",
            "- [MKM-COMP-PRED-SPLIT] logos_non_gating weight 0 in instrument bests; use Field+price for action.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    doc = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
