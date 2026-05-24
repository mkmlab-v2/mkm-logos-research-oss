#!/usr/bin/env python3
"""One-screen B-track bundle: CJK substitution + sweep + wire AB pointers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports/constitution/btrack_pilot"
OUT = PILOT / "comp_ijeoma_cjk_hypo_bundle_summary_v1.json"

PATHS = {
    "substitution_eval": PILOT / "comp_ijeoma_cjk_substitution_hypo_eval_v1.json",
    "sweep_baseline": PILOT / "comp_universal_bench_matrix_sweep_ijeoma_chunk_cjk_ascii_compact_v1.json",
    "lane_cjk_ascii": ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_ascii_compact_v1.json",
    "char_jaccard": PILOT / "comp_ijeoma_cjk_fidelity_char_jaccard_v1.json",
    "wire_chunk_subst": PILOT / "comp_universal_bench_matrix_wire_ab_ijeoma_chunk_cjk_hypo_v1.json",
    "wire_chunk_subst_legacy": PILOT / "comp_universal_bench_matrix_wire_ab_ijeoma_chunk_cjk_on_the_fly_v1.json",
    "parity_bridge_hook": PILOT / "comp_ijeoma_cjk_bridge_vs_eval_hook_v1.json",
    "saving_tune_ab": PILOT / "comp_ijeoma_cjk_saving_tune_ab_v1.json",
    "lane_cjk": ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_hypo_v1.json",
    "lane_cjk_o200k_tight": ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_o200k_tight_v1.json",
    "sweep_billing_o200k_tight": PILOT / "comp_universal_bench_matrix_sweep_ijeoma_chunk_cjk_o200k_tight_v1.json",
    "sweep_470": PILOT / "comp_universal_bench_matrix_sweep_v1.json",
    "o200k_bench": PILOT / "comp_ijeoma_cjk_o200k_bench_v1.json",
    "o200k_diagnosis": PILOT / "comp_ijeoma_cjk_o200k_diagnosis_v1.json",
    "marker_strategy_ab": PILOT / "comp_ijeoma_cjk_marker_strategy_ab_v1.json",
    "o200k_marker_sweep": PILOT / "comp_ijeoma_cjk_o200k_marker_sweep_v1.json",
    "hook_billing_mode_compare": PILOT / "comp_ijeoma_cjk_hook_billing_mode_compare_v1.json",
    "hook_billing_mode_env_parity": PILOT / "comp_ijeoma_cjk_bridge_vs_eval_hook_billing_mode_env_v1.json",
    "ms_hwpx_cjk_footnote": ROOT / "reports/hwpx_poc/ms_cjk_billing_footnote_paste_v1.txt",
    "lexicon_cap_sweep": PILOT / "comp_ijeoma_hanja_lexicon_cap_sweep_v1.json",
    "ms_hwpx_crosslink": ROOT / "reports/hwpx_poc/ms_cjk_btrack_crosslink_v1.json",
}


def _load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main() -> int:
    sub = _load(PATHS["substitution_eval"])
    sweep = _load(PATHS["sweep_baseline"])
    cj = _load(PATHS["char_jaccard"])
    wire = _load(PATHS["wire_chunk_subst"])

    bundle = {
        "schema": "comp_ijeoma_cjk_hypo_bundle_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "headline": {
            "substitution_mean_saving": (sub or {}).get("mean_token_saving_rate_cjk_substitution"),
            "substitution_cases_evaluated": (sub or {}).get("cases_evaluated"),
            "substitution_marker_strategy": (sub or {}).get("marker_strategy"),
            "sweep_baseline_mean_saving_90": (
                (sweep or {}).get("profiles", {}).get("economy", {}).get("mean")
            ),
            "eval_hook_mean_saving_90": (
                (_load(PILOT / "comp_universal_bench_matrix_sweep_ijeoma_chunk_eval_hook_v1.json") or {})
                .get("profiles", {})
                .get("economy", {})
                .get("mean")
            ),
            "mean_char_jaccard_90": (cj or {}).get("mean_char_jaccard"),
            "wire_ab_saving_pct": (wire or {}).get("headline", {}).get("wire_saving_pct")
            or (wire or {}).get("headline", {}).get("economy_saving_pct"),
            "saving_tune_ab_profiles": ( _load(PATHS["saving_tune_ab"]) or {}).get("profiles"),
            "parity_ok": ( _load(PATHS["parity_bridge_hook"]) or {}).get("parity_ok"),
            "matrix_sweep_470_cases": (_load(PATHS["sweep_470"]) or {}).get("case_count"),
            "mean_o200k_saving_90": (_load(PATHS["o200k_bench"]) or {}).get(
                "mean_o200k_token_saving_rate"
            ),
            "corpus_o200k_saving_90": (_load(PATHS["o200k_bench"]) or {}).get(
                "corpus_o200k_token_saving_rate"
            ),
            "o200k_negative_case_count": (_load(PATHS["o200k_diagnosis"]) or {}).get(
                "negative_o200k_per_case_count"
            ),
            "corpus_o200k_tight_90": (_load(PILOT / "comp_ijeoma_cjk_o200k_diagnosis_o200k_tight_v1.json") or {}).get(
                "corpus_o200k_saving_rate"
            ),
            "o200k_billing_kpi_note": (
                "Hook default ascii_compact: proxy ~57.6%, o200k corpus ~-2% (operational). "
                "o200k_tight markers: corpus o200k ~+32% (90-case, tiktoken; B-track billing research only). "
                "PUA legacy ~30.8% proxy / ~-20% o200k. Not MS 47.5% or 290 MD headline."
            ),
            "marker_strategy_ab": (_load(PATHS["marker_strategy_ab"]) or {}).get("recommendation"),
            "o200k_marker_sweep": (_load(PATHS["o200k_marker_sweep"]) or {}).get("recommendation"),
            "billing_lane_sweep_mean_90": (
                (_load(PATHS["sweep_billing_o200k_tight"]) or {})
                .get("profiles", {})
                .get("economy", {})
                .get("mean")
            ),
            "hook_billing_mode": (_load(PATHS["hook_billing_mode_compare"]) or {}).get("alignment"),
            "lexicon_cap_sweep_sample": (_load(PATHS["lexicon_cap_sweep"]) or {}).get("profiles"),
        },
        "artifacts": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in PATHS.items() if v.is_file()},
        "do_not_promote": [
            "Not Golden 40 MS 47.5%",
            "Not 290 MD matrix KPI mean",
            "Not Track A active report",
        ],
    }
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "headline": bundle["headline"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
