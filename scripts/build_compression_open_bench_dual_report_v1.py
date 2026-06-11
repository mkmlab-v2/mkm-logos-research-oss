#!/usr/bin/env python3
"""[HYPO] Open Bench dual-report summary — raw metrics per corpus/SKU (no Track A SLA merge)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
SCHEMA = "compression_open_bench_dual_report_v1"

SOURCES: list[tuple[str, Path, str]] = [
    ("golden40_public_safe_stateless", ROOT / "reports/customer_compression_stateless_poc_golden40_public_safe_v1_latest.json", "compression_api_golden40_public_safe"),
    ("golden40_public_safe_routed", ROOT / "reports/customer_compression_stateless_poc_golden40_public_safe_routed_v1_latest.json", "MKM-CHAT-D1"),
    ("open_structured", ROOT / "reports/customer_compression_stateless_poc_open_structured_v1_latest.json", "compression_api_open_structured"),
    ("open_structured_long", ROOT / "reports/customer_compression_stateless_poc_open_structured_long_v1_latest.json", "compression_api_open_structured_long"),
    ("sku_MKm_SCM_A1", ROOT / "reports/customer_compression_stateless_poc_scm_a1_v1_latest.json", "MKM-SCM-A1"),
    ("sku_MKm_CHAT_D1", ROOT / "reports/customer_compression_stateless_poc_chat_d1_v1_latest.json", "MKM-CHAT-D1"),
    ("sku_MKm_FIN_E1", ROOT / "reports/customer_compression_stateless_poc_fin_e1_v1_latest.json", "MKM-FIN-E1"),
    ("sku_MKm_MED_G1", ROOT / "reports/customer_compression_stateless_poc_med_g1_v1_latest.json", "MKM-MED-G1"),
]

TRACK_A_REF = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _row_from_poc(label: str, path: Path, sku_id: str) -> dict[str, Any]:
    doc = _load(path)
    if not doc:
        return {"label": label, "sku_id": sku_id, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "present": False}
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    raw_rate = agg.get("mean_token_saving_rate_proxy")
    raw_j = agg.get("mean_jaccard_proxy")
    repair = doc.get("repair_v2_aggregate") if isinstance(doc.get("repair_v2_aggregate"), dict) else {}
    repair_rate = repair.get("mean_token_saving_rate_proxy")
    repair_j = repair.get("mean_jaccard_proxy")
    if repair_rate is None:
        repair_rate = raw_rate
        repair_j = raw_j
    delta_align = None
    if isinstance(raw_rate, (int, float)) and isinstance(repair_rate, (int, float)):
        delta_align = round(float(repair_rate) - float(raw_rate), 6)
    sku_ctx = doc.get("sku_context") if isinstance(doc.get("sku_context"), dict) else {}
    return {
        "label": label,
        "sku_id": sku_id,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "present": True,
        "case_count": doc.get("case_count"),
        "forced_shard_id": sku_ctx.get("forced_shard_id"),
        "raw": {
            "mean_token_saving_rate_proxy": raw_rate,
            "mean_jaccard_proxy": raw_j,
            "saving_pct_display": round(float(raw_rate) * 100, 2) if isinstance(raw_rate, (int, float)) else None,
        },
        "repair_v2": {
            "mean_token_saving_rate_proxy": repair_rate,
            "mean_jaccard_proxy": repair_j,
            "repair_applied_count": repair.get("repair_applied_count", 0),
            "note": repair.get("note") or "stateless PoC — repair layer often identical to raw",
        },
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": delta_align,
            "token_saving_rate_delta_repair_v2_minus_raw": delta_align,
        },
        "non_zero_saving": isinstance(raw_rate, (int, float)) and float(raw_rate) > 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rows = [_row_from_poc(label, path, sku) for label, path, sku in SOURCES]
    present = [r for r in rows if r.get("present")]
    non_zero = [r for r in present if r.get("non_zero_saving")]

    track_a = _load(TRACK_A_REF) or {}
    track_a_kpi = {
        "global_token_saving_rate": track_a.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": track_a.get("avg_reconstruction_fidelity_jaccard"),
        "note": "Frozen Track A 40-case bench — NOT a guarantee on open-bench corpora",
    }

    primary_routed = next(
        (r for r in present if r.get("label") == "golden40_public_safe_routed" and r.get("non_zero_saving")),
        None,
    )
    illustrative_roi: list[dict[str, Any]] = []
    if primary_routed:
        rate = float((primary_routed.get("raw") or {}).get("mean_token_saving_rate_proxy") or 0)
        for spend in (100_000_000, 500_000_000, 1_000_000_000):
            save = round(spend * rate)
            illustrative_roi.append(
                {
                    "assumption_monthly_llm_spend_krw": spend,
                    "applied_saving_rate": rate,
                    "illustrative_monthly_save_krw": save,
                    "illustrative_annual_save_krw": save * 12,
                    "disclaimer_ko": "가정·시나리오 — 실고객 ROI 아님",
                }
            )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "positioning_ref": "docs/final/artifacts/mkm_b2b_compression_positioning_external_v1_latest.json",
        "persuasion_deck_ref": "docs/final/artifacts/compression_open_bench_persuasion_deck_v1_latest.json",
        "forbidden_headline": [
            "Claim 47.5% on open-bench without citing this corpus label and measured raw %",
            "SKU PoC % as Track A SLA",
            "repair_v2 uplift as core model proof",
        ],
        "track_a_reference_only": track_a_kpi,
        "corpora_and_skus": rows,
        "summary": {
            "reports_present": len(present),
            "reports_non_zero_saving": len(non_zero),
            "any_non_zero": len(non_zero) > 0,
        },
        "allowed_headline_template_ko": (
            "공개·마스킹 코퍼스 {label} N={case_count}건 조건에서 "
            "raw 절감 {saving_pct}% · Jaccard {jaccard} (Track A 47.5%와 동일 보장 아님)"
        ),
        "json_corpus_positioning": {
            "strategy": "short_prose_strength_not_json_failure",
            "note_ko": (
                "open_structured JSON-heavy 0%는 코퍼스 조건 한계로 보고 — "
                "엔진 실패 단정·Track A SLA 합선 금지"
            ),
        },
        "illustrative_roi_scenarios_krw": illustrative_roi,
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"present={len(present)} non_zero={len(non_zero)}")
    for r in non_zero:
        print(
            f"  {r['label']}: raw={r['raw'].get('saving_pct_display')}% "
            f"J={r['raw'].get('mean_jaccard_proxy')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
