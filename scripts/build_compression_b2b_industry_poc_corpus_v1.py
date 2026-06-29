#!/usr/bin/env python3
"""Build masked public-safe industry PoC JSONL corpora for B2B off-the-shelf SKUs. [HYPO]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "compression"

CORPORA: dict[str, dict[str, Any]] = {
    "stateless_poc_scm_public_safe_v1.jsonl": {
        "external_sku": "MKM-SCM-A1",
        "domain_tag": "scm-b2b-demo",
        "rows": [
            "공급망 SCM 대시보드에서 BOM 변경 후 리드타임이 2일 연장되었으나 재고 안전분은 policy 범위 내입니다.",
            "생산계획 조정 시 물류 허브별 조달 리드타임 variance를 주간 리포트로만 공유합니다.",
            "재고 회전율 하락 구간에서 SCM 알림은 내부 검토용이며 고객 SLA 약속이 아닙니다.",
            "BOM 정합성 검사 후 공급망 리스크 라벨만 마스킹한 샘플 로그입니다.",
            "조달 지연 시 생산계획 fallback은 research_only PoC 시나리오입니다.",
            "물류 트래킹 API 응답을 SCM 운영 문장으로 요약한 fictional demo row.",
            "재고 snapshot과 리드타임 forecast는 synthetic data이며 실거래 트리거가 아닙니다.",
            "공급망 KPI 문장 압축 PoC용 — Track A 47.5% 보장 문구 금지.",
            "BOM diff 리뷰 노트: supplier lead time buffer 48h applied in planning sandbox.",
            "SCM ops weekly: procurement queue stable; logistics ETA noise within tolerance band.",
        ],
    },
    "stateless_poc_chat_public_safe_v1.jsonl": {
        "external_sku": "MKM-CHAT-D1",
        "domain_tag": "chatbot-b2b-demo",
        "rows": [
            "FAQ intent 라우팅 후 챗봇 세션 응답 latency를 내부 벤치로만 측정합니다.",
            "고객지원 대화 로그는 PII 마스킹된 fictional transcript입니다.",
            "프롬프트 guardrail 위반 intent는 escalate-to-human policy로만 기록합니다.",
            "chatbot session summary: FAQ match rate proxy for compression PoC only.",
            "대화 턴 12에서 intent drift가 감지되었으나 자동 주문 트리거는 없습니다.",
            "응답 품질 리뷰는 research_only이며 프로덕션 SLA가 아닙니다.",
            "Support bot PoC row with masked user id and synthetic FAQ body text.",
            "세션 종료 시 chatbot transcript hash만 남기고 원문은 stateless packet으로 처리합니다.",
            "Intent classifier confidence below threshold triggers manual QA queue.",
            "Customer support macro reply draft for compression measurement — no live send.",
        ],
    },
    "stateless_poc_finance_public_safe_v1.jsonl": {
        "external_sku": "MKM-FIN-E1",
        "domain_tag": "finance-disclosure-b2b-demo",
        "rows": [
            "분기 공시보고서 초안의 재무제표 감사 항목과 ESG 컴플라이언스 리스크를 내부 검토합니다.",
            "규제 공시 일정 전 리스크 disclosure 문장은 마스킹된 fictional issuer 데이터입니다.",
            "감사 의견 초안은 고객 실측 전 research_only PoC이며 SLA 약속이 아닙니다.",
            "Compliance checklist row: regulatory filing deadline T+5 with internal hold gate.",
            "재무제표 주석 압축 PoC — trading PnL 키워드와 혼동 금지.",
            "ESG metrics appendix uses synthetic numbers; no market trigger.",
            "공시 draft review notes risk and compliance caveats for token reduction demo.",
            "Regulatory disclosure template stress text for stateless compression measurement.",
            "Audit trail references masked ledger ids only; no customer identity.",
            "Financial report section summary for compression PoC — not a performance warranty.",
        ],
    },
    "stateless_poc_health_public_safe_v1.jsonl": {
        "external_sku": "MKM-MED-G1",
        "domain_tag": "health-b2b-demo",
        "rows": [
            "건강검진 SOAP 노트에서 환자 바이탈과 임상 진단 보조 라벨만 마스킹 처리했습니다.",
            "Silver Tech wellness 리포트는 의료 결정을 대체하지 않으며 research_only PoC입니다.",
            "임상 요약 문장 압축 데모 — 실제 환자 식별 정보는 포함하지 않습니다.",
            "Patient vitals trend paragraph with fictional case id HEALTH-DEMO-07.",
            "의료 기록 요약은 HIPAA-style masking applied; not for clinical gating.",
            "Diagnostic assist text is non-gating and must not trigger live care actions.",
            "SOAP subjective/objective lines compressed for token PoC measurement only.",
            "Health screening follow-up note: vitals stable in synthetic cohort row.",
            "Clinical documentation sample for B2B compression demo — counsel review pending.",
            "Wellness coaching transcript masked; no treatment recommendation implied.",
        ],
    },
}

# Deterministic expansion templates per domain (rows 11–30)
_EXPAND_SUFFIX_KO = [
    " 내부 검토용 PoC 문장이며 고객 SLA가 아닙니다.",
    " research_only 샘플로 실거래 트리거가 없습니다.",
    " 마스킹된 fictional demo 데이터입니다.",
    " Track A 47.5% 보장 문구와 혼용 금지.",
    " stateless packet 측정 전용 row입니다.",
]


def _expand_rows(base_rows: list[str], target: int) -> list[str]:
    if len(base_rows) >= target:
        return base_rows[:target]
    out = list(base_rows)
    i = 0
    while len(out) < target:
        base = base_rows[i % len(base_rows)]
        suffix = _EXPAND_SUFFIX_KO[(len(out) - len(base_rows)) % len(_EXPAND_SUFFIX_KO)]
        variant = f"{base.rstrip('.')} · variant-{len(out)+1:02d}.{suffix}"
        out.append(variant)
        i += 1
    return out


def _row(
    *,
    row_id: str,
    domain_tag: str,
    external_sku: str,
    text: str,
) -> dict[str, Any]:
    return {
        "id": row_id,
        "source": "compression_b2b_industry_poc_corpus_v1",
        "domain_tag": domain_tag,
        "external_sku": external_sku,
        "text": text,
        "public_safe": True,
        "forbidden_as_customer_sla": True,
        "research_only": True,
    }


def build_all(out_dir: Path = OUT_DIR, *, rows_per_sku: int = 10) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, spec in CORPORA.items():
        path = out_dir / filename
        lines: list[str] = []
        sku = str(spec["external_sku"])
        tag = str(spec["domain_tag"])
        for i, text in enumerate(_expand_rows(spec["rows"], rows_per_sku), start=1):
            slug = filename.replace("stateless_poc_", "").replace("_public_safe_v1.jsonl", "")
            rid = f"b2b_{slug}_{i:02d}"
            lines.append(json.dumps(_row(row_id=rid, domain_tag=tag, external_sku=sku, text=text), ensure_ascii=False))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Build B2B industry PoC JSONL corpora.")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--rows-per-sku", type=int, default=10, help="Target rows per SKU (default 10; B1 uses 30)")
    args = ap.parse_args()
    paths = build_all(args.out_dir.resolve(), rows_per_sku=max(1, args.rows_per_sku))
    for p in paths:
        print(f"Wrote {p}")
    print(f"count={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
