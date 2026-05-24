#!/usr/bin/env python3
"""MS-PASTE / HWPX fact block + CJK B-track bundle cross-link (paste-only, no KPI merge)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_hypo_bundle_summary_v1.json"
HOOK_BILLING = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_hook_billing_mode_compare_v1.json"
GOLDEN_NOTE = "Golden 40 frozen ~47.5% — MS-PASTE only; do not merge CJK hypo."
OUT_TXT = ROOT / "reports/hwpx_poc/ms_cjk_btrack_crosslink_v1.txt"
OUT_JSON = ROOT / "reports/hwpx_poc/ms_cjk_btrack_crosslink_v1.json"
HWPX_FILLED = ROOT / "reports/hwpx_poc/ms_microsoft_ma_jung_filled_v1.hwpx"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8")) if BUNDLE.is_file() else {}
    hook_bill = json.loads(HOOK_BILLING.read_text(encoding="utf-8")) if HOOK_BILLING.is_file() else {}
    h = bundle.get("headline") or {}

    lines = [
        "[MS-PASTE / HWPX — CJK B-track cross-link · research_only]",
        GOLDEN_NOTE,
        "",
        "Universal Matrix 290 operational (excl. chunk lanes):",
        "  economy mean saving ~64.57% | Jaccard ~0.82",
        "  artifact: reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_470_subset_290_v1.json",
        "",
        "Ijeoma chunk CJK substitution [HYPO] (separate bucket — NOT in 290 mean):",
        f"  90-case baseline saving ~{(h.get('sweep_baseline_mean_saving_90') or 0)*100:.1f}%",
        f"  char Jaccard {h.get('mean_char_jaccard_90')}",
        f"  wire AB saving {h.get('wire_ab_saving_pct')}% | parity_ok={h.get('parity_ok')}",
        f"  bundle: {BUNDLE.relative_to(ROOT).as_posix()}",
        "",
        "OpenAI o200k_base billing (hook=ascii_compact; NOT comparable to proxy):",
        f"  hook lane corpus o200k ~{(h.get('corpus_o200k_saving_90') or 0)*100:.1f}% (near break-even)",
        f"  o200k_tight markers corpus ~{(h.get('corpus_o200k_tight_90') or 0)*100:.1f}% "
        "[HYPO billing lane on disk; separate from hook default]",
        f"  billing lane artifact: docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_o200k_tight_v1.json",
        f"  billing sweep mean proxy ~{(h.get('billing_lane_sweep_mean_90') or 0)*100:.1f}%",
        "",
        "Hook billing experiment (env o200k_tight vs ascii_compact on chunk_table):",
        f"  ops parity_ok={hook_bill.get('operational_hook', {}).get('parity_ok')}",
        f"  billing hook parity_ok={hook_bill.get('billing_hook_experiment', {}).get('parity_ok')}",
        f"  hook o200k aligned with billing lane file={hook_bill.get('alignment', {}).get('hook_o200k_matches_billing_lane_sweep')}",
        "",
        "Marker strategy AB [HYPO] (comp_ijeoma_cjk_marker_strategy_ab_v1.json):",
        "  ascii_compact: proxy ~57.6% | o200k ~-2%",
        "  o200k_tight: proxy ~57.6% | o200k corpus ~+32% (0 negative cases / 90)",
        "  PUA legacy: proxy ~30.8% | o200k ~-20%",
        "  atom_id — o200k unusable; B-track research only",
        "",
        "Do not paste CJK proxy % as Golden 47.5% or 290 MD headline.",
    ]
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    doc = {
        "schema": "ms_cjk_btrack_crosslink_v1",
        "generated_at_utc": _utc(),
        "ms_paste_only": True,
        "golden_frozen_note": GOLDEN_NOTE,
        "hwpx_filled_path": str(HWPX_FILLED.relative_to(ROOT)).replace("\\", "/")
        if HWPX_FILLED.is_file()
        else None,
        "cjk_bundle_headline": h,
        "paste_txt": str(OUT_TXT.relative_to(ROOT)).replace("\\", "/"),
        "matrix_290_artifact": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_470_subset_290_v1.json",
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if BUNDLE.is_file():
        bundle["ms_hwpx_crosslink"] = {
            "paste_txt": doc["paste_txt"],
            "crosslink_json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
        }
        BUNDLE.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"wrote_txt": OUT_TXT.name, "wrote_json": OUT_JSON.name}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
