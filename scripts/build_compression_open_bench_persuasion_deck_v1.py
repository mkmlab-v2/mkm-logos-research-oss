#!/usr/bin/env python3
"""[HYPO] Internal B2B persuasion deck — illustrative ROI from open-bench metrics (SEND_GATE HOLD)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DUAL_DEFAULT = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
SWEEP_DEFAULT = ROOT / "reports/compression_open_bench_research_sweep_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/compression_open_bench_persuasion_deck_v1_latest.json"
CHAT_LITERAL_VARIANT = "routed_literal_b2b_overlay"
SCHEMA = "compression_open_bench_persuasion_deck_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _routed_primary(dual: dict[str, Any]) -> dict[str, Any] | None:
    for row in dual.get("corpora_and_skus") or []:
        if row.get("label") == "golden40_public_safe_routed" and row.get("present"):
            return row
    for row in dual.get("corpora_and_skus") or []:
        if row.get("non_zero_saving"):
            return row
    return None


def _illustrative_roi(monthly_spend_krw: int, saving_rate: float) -> dict[str, Any]:
    monthly_save = round(monthly_spend_krw * saving_rate)
    return {
        "assumption_monthly_llm_spend_krw": monthly_spend_krw,
        "applied_saving_rate": saving_rate,
        "illustrative_monthly_save_krw": monthly_save,
        "illustrative_annual_save_krw": monthly_save * 12,
        "disclaimer_ko": "가정·시나리오 전용 — 실고객 invoice·계약 ROI 아님",
    }


def _sweep_literal_chat(sweep_path: Path | None) -> dict[str, Any] | None:
    if not sweep_path or not sweep_path.is_file():
        return None
    sweep = _load(sweep_path)
    for v in sweep.get("variants") or []:
        if v.get("variant_id") == CHAT_LITERAL_VARIANT and v.get("present"):
            raw = v.get("raw") or {}
            rate = raw.get("mean_token_saving_rate_proxy")
            if isinstance(rate, (int, float)) and float(rate) > 0:
                return {
                    "variant_id": CHAT_LITERAL_VARIANT,
                    "sku_id": v.get("sku"),
                    "compression_profile": v.get("compression_profile"),
                    "case_count": v.get("case_count"),
                    "evidence_sweep": _rel(sweep_path),
                    "raw": {
                        "mean_token_saving_rate_proxy": float(rate),
                        "saving_pct_display": raw.get("saving_pct_display"),
                        "mean_jaccard_proxy": raw.get("mean_jaccard_proxy"),
                    },
                    "jaccard_tradeoff_ko": (
                        "literal 프로파일 — economy 대비 절감↑·Jaccard proxy↓. "
                        "내부 미팅·[HYPO] 시나리오만; 대외 헤드라인·Track A 승격 없음."
                    ),
                }
    return None


def build(*, dual_path: Path, sweep_path: Path | None = None) -> dict[str, Any]:
    dual = _load(dual_path)
    primary = _routed_primary(dual)
    if not primary:
        raise SystemExit("no routed non-zero row in dual report")

    raw = primary.get("raw") or {}
    saving_rate = float(raw.get("mean_token_saving_rate_proxy") or 0)
    jaccard = raw.get("mean_jaccard_proxy")
    case_count = primary.get("case_count")
    sku = primary.get("sku_id")
    literal_anchor = _sweep_literal_chat(sweep_path)

    scenarios = [
        _illustrative_roi(100_000_000, saving_rate),
        _illustrative_roi(500_000_000, saving_rate),
        _illustrative_roi(1_000_000_000, saving_rate),
    ]
    literal_scenarios: list[dict[str, Any]] = []
    if literal_anchor:
        lit_rate = float(literal_anchor["raw"]["mean_token_saving_rate_proxy"])
        literal_scenarios = [
            _illustrative_roi(100_000_000, lit_rate),
            _illustrative_roi(500_000_000, lit_rate),
            _illustrative_roi(1_000_000_000, lit_rate),
        ]

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "lane": "internal_persuasion_deck_only",
        "evidence_dual_report": _rel(dual_path),
        "evidence_research_sweep": _rel(sweep_path) if sweep_path and sweep_path.is_file() else None,
        "measured_anchor": {
            "corpus_label": primary.get("label"),
            "sku_id": sku,
            "forced_shard_id": primary.get("forced_shard_id"),
            "case_count": case_count,
            "raw": {
                "mean_token_saving_rate_proxy": saving_rate,
                "saving_pct_display": raw.get("saving_pct_display"),
                "mean_jaccard_proxy": jaccard,
            },
            "repair_v2_note": "repair_applied_count typically 0 — cite raw; delta=0",
            "track_a_sla_equivalent": False,
            "role": "public_open_bench_anchor_economy",
        },
        "btrack_research_anchor_literal": literal_anchor,
        "illustrative_roi_scenarios_krw": scenarios,
        "illustrative_roi_scenarios_literal_krw": literal_scenarios,
        "json_corpus_positioning": {
            "strategy": "short_prose_strength_not_json_failure",
            "open_structured_measured_saving_pct": 0.0,
            "note_ko": (
                "JSON-heavy open_structured 0%는 엔진 고장이 아니라 코퍼스·must_keep·라우팅 조건 미충족으로 보고. "
                "대외 수치는 golden40_routed·산업 SKU PoC(8–11%)를 코퍼스별로 분리 인용."
            ),
        },
        "allowed_internal_headline_ko": (
            f"오픈 코퍼스 golden40 N={case_count} · {sku} — economy raw {raw.get('saving_pct_display')}% "
            f"(J {jaccard})"
            + (
                f"; B-track literal 연구 {literal_anchor['raw'].get('saving_pct_display')}% "
                f"(J {literal_anchor['raw'].get('mean_jaccard_proxy')}) — 내부만"
                if literal_anchor
                else ""
            )
            + " · Track A SLA 비동일 · SEND_GATE HOLD · illustrative ROI는 가정치"
        ),
        "forbidden_headline_ko": [
            "연간 12억 순이익 보장",
            "글로벌 표준 데이터셋 전수 적용",
            "Jaccard proxy를 엔터프라이즈 보안 무결성 90%로 단정",
            "Track A 47.5%와 동일 SLA",
            "언론·광고 송출 준비 완료",
        ],
        "tone_ratio": "70/20/10",
        "structure": {
            "opening_ko": "결론: 조건부 raw 절감 실측 있음 — 대외 send는 HOLD",
            "body_ko": (
                "CFO 시나리오는 illustrative만; economy anchor=dual report, "
                "literal 15%대=B-track sweep(내부 시나리오)"
            ),
            "closing_ko": "다음 게이트: 실고객 마스킹 JSONL PoC · counsel sign-off",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dual-json", type=Path, default=DUAL_DEFAULT)
    ap.add_argument("--sweep-json", type=Path, default=SWEEP_DEFAULT)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args(argv)

    dual_path = args.dual_json if args.dual_json.is_absolute() else ROOT / args.dual_json
    if not dual_path.is_file():
        raise SystemExit(f"missing dual report: {dual_path}")
    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json

    doc = build(dual_path=dual_path, sweep_path=sweep_path if sweep_path.is_file() else None)
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    pct = (doc["measured_anchor"]["raw"] or {}).get("saving_pct_display")
    print(f"anchor={pct}% send_gate={doc['send_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
