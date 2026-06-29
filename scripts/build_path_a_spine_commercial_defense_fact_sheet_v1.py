#!/usr/bin/env python3
"""Assemble Path A spine commercial defense fact sheet — honest GTM / OI paste guard.

research_only product lane metrics · send_gate HOLD · no ACTIVE apply.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json"
OUT_PASTE = ROOT / "reports/human_paste/path_a_spine_commercial_defense_fact_sheet_v1_latest.txt"
B2B_BENCH = ROOT / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_B2B_SPINE_BENCH_INPUT_V1.json"
B2B_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_b2b_spine_binary_billable_eval_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _pct(rate: float | None) -> str:
    if rate is None:
        return "n/a"
    return f"{float(rate) * 100:.2f}%"


def build() -> dict[str, Any]:
    microgrid = _load("reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json") or {}
    signoff = _load("reports/ng40_path_a_product_signoff_chain_v1_latest.json") or {}
    masked = _load("reports/ng40_path_a_customer_masked_cohort_chain_v1_latest.json") or {}
    closure = _load("reports/compression_multilens_dr_closure_v1_latest.json") or {}
    dual = _load("reports/compression_golden40_active_dual_report_v1_latest.json") or {}
    b2b_eval = _load(str(B2B_EVAL.relative_to(ROOT)).replace("\\", "/")) if B2B_EVAL.is_file() else None

    b2b_block = microgrid.get("b2b_longform") or {}
    canonical = (b2b_block.get("knees") or {}).get("canonical_0_88") or {}
    spine_rate = float(canonical.get("global_token_saving_rate_spine_binary_only") or 0.222911)
    byte_exact = float(canonical.get("byte_exact_subset_parity") or 0)
    case_count = int(canonical.get("case_count") or (b2b_eval or {}).get("aggregate", {}).get("case_count") or 34)

    if b2b_eval:
        agg = b2b_eval.get("aggregate") or {}
        spine_rate = float(agg.get("global_token_saving_rate_spine_binary_billable") or spine_rate)
        byte_exact = float(agg.get("byte_exact_subset_parity") or byte_exact)
        case_count = int(agg.get("case_count") or case_count)

    masked_spine = (masked.get("path_a_spine_eval") or {})
    repair_delta = (dual.get("delta") or {}).get("alignment_pass_rate_delta_repair_v2_minus_raw")

    latent_active = (closure.get("kpi_lanes") or {}).get("latent_g40_active") or {}
    v3 = (closure.get("kpi_lanes") or {}).get("latent_g40_conditional_v3") or {}

    doc = {
        "schema": "path_a_spine_commercial_defense_fact_sheet_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "product_lane": {
            "headline_kpi": "spine_binary_billable_only",
            "global_token_saving_rate": round(spine_rate, 6),
            "global_token_saving_percent": round(spine_rate * 100, 2),
            "byte_exact_subset_parity": byte_exact,
            "case_count": case_count,
            "cohort": {
                "bench_input": str(B2B_BENCH.relative_to(ROOT)).replace("\\", "/"),
                "domain_tag": "finance_macro_b2b",
                "min_raw_utf8_bytes": 256,
                "description_ko": "B2B longform macro alert / offer copy — spine official recon only",
            },
            "codec": {
                "official_recon": "verbatim_spine_decode_binary(MKVS)",
                "sidecar_role": "NON_GATING preview — not official recon quality",
                "spine_invariant_note_ko": "keep_ratio 0.78–0.92 sweep에서 spine saving 동일",
            },
            "canonical_keep_ratio": 0.88,
            "product_ready": bool((signoff.get("product_gates") or {}).get("product_ready")),
            "eval_pointer": str(B2B_EVAL.relative_to(ROOT)).replace("\\", "/") if B2B_EVAL.is_file() else None,
        },
        "research_lanes_do_not_merge": {
            "latent_g40_active": {
                "global_token_saving_rate": latent_active.get("global_token_saving_rate"),
                "avg_jaccard": latent_active.get("avg_reconstruction_fidelity_jaccard"),
                "label": "B-track research — not B2B billing headline",
            },
            "latent_g40_conditional_v3": {
                "global_token_saving_rate": v3.get("global_token_saving_rate"),
                "min_jaccard": v3.get("min_reconstruction_fidelity_jaccard"),
                "beat_frozen": (closure.get("pareto_signoff") or {}).get("beat_frozen"),
                "label": "research_only conditional fusion",
            },
            "masked_support_cohort_25row": {
                "spine_saving": masked_spine.get("global_token_saving_rate_spine_binary"),
                "byte_exact": masked_spine.get("byte_exact_subset_parity"),
                "note_ko": "합성 support-chat masked — 실고객 ROI·OI 주장 금지",
            },
        },
        "repair_v2": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": repair_delta,
            "label": "operational post-processor only — not base-model quality",
        },
        "forbidden_paste_phrases": [
            "47% compression solved",
            "beat_frozen ACTIVE",
            "v3 conditional as production SLA",
            "masked cohort 0.18% as customer ROI",
            "repair_v2 uplift as core model proof",
        ],
        "allowed_paste_phrases": [
            f"B2B longform spine binary billable ~{_pct(spine_rate)} byte_exact",
            "official recon = verbatim spine only; sidecar preview separate",
            "reproduce: py scripts/run_path_a_spine_commercial_defense_chain_v1.py",
        ],
        "reproduce": {
            "chain": "py scripts/run_path_a_spine_commercial_defense_chain_v1.py",
            "microgrid": "py scripts/run_ng40_path_a_keep_ratio_microgrid_v1.py",
            "b2b_spine_eval": (
                "py scripts/run_nextgen_spine_binary_billable_eval_v1.py "
                "--bench-input experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_B2B_SPINE_BENCH_INPUT_V1.json "
                "--out-json experiments/nextgen_clean_slate_cpu_v1/results/ng40_b2b_spine_binary_billable_eval_v1_latest.json "
                "--arm-id ng40_b2b_spine_binary_billable_v1 --bench-label b2b_longform"
            ),
        },
        "pointers": {
            "microgrid": "reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json",
            "product_signoff": "reports/ng40_path_a_product_signoff_chain_v1_latest.json",
            "dr_closure": "reports/compression_multilens_dr_closure_v1_latest.json",
        },
    }
    return doc


def _paste_lines(doc: dict[str, Any]) -> list[str]:
    p = doc["product_lane"]
    return [
        "Path A spine — commercial defense fact sheet (internal · send_gate HOLD)",
        "",
        "■ Honest product KPI (B2B longform)",
        f"  saving (spine binary billable): {_pct(p.get('global_token_saving_rate'))}",
        f"  byte_exact_subset_parity: {p.get('byte_exact_subset_parity')}",
        f"  cases: {p.get('case_count')} · domain: finance_macro_b2b",
        f"  product_ready: {p.get('product_ready')}",
        "",
        "■ Official recon contract",
        "  decode = verbatim_spine_decode_binary(MKVS) only",
        "  sidecar = preview / metrics — NON_GATING",
        "",
        "■ Do NOT paste to OI / grant / GTM",
        "  - latent 47% / v3 conditional / beat_frozen",
        "  - masked 25-row ~0.18% as customer ROI",
        "  - repair_v2 as core model quality",
        "",
        "■ Reproduce",
        f"  {doc['reproduce']['chain']}",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-paste", type=Path, default=OUT_PASTE)
    args = ap.parse_args()

    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_paste.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_paste.write_text("\n".join(_paste_lines(doc)) + "\n", encoding="utf-8")

    ok = (
        doc["product_lane"]["byte_exact_subset_parity"] >= 1.0
        and doc["product_lane"]["global_token_saving_rate"] > 0
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "wrote_json": str(args.out_json),
                "wrote_paste": str(args.out_paste),
                "saving_percent": doc["product_lane"]["global_token_saving_percent"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
