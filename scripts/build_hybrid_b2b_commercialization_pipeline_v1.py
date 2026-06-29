#!/usr/bin/env python3
"""Refresh hybrid B2B commercialization pipeline SSOT (Compression vs Edge SKU-COORD lanes)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.md"

SIGNOFF = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"
ROI = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"
LAUNCH = ROOT / "docs/final/artifacts/a_codeai_public_benchmark_launch_checklist_v1.json"
EDGE = ROOT / "docs/final/artifacts/edge_encoder_spec_v1_latest.json"
INTAKE = ROOT / "docs/final/artifacts/patient_intake_send_gate_v1_latest.json"
WORKFLOW = ROOT / "docs/final/artifacts/compression_b2b_recommended_workflow_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


CUSTOMER_PROXY_POC = (
    ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json"
)
REHEARSAL_MARKERS = ("rehearsal", "prospect-rehearsal")


def _aggregate_from_poc(path: Path, source: str) -> tuple[float | None, float | None, int | None, str]:
    if not path.is_file():
        return None, None, None, "missing"
    poc = json.loads(path.read_text(encoding="utf-8-sig"))
    agg = poc.get("aggregate") or {}
    saving = agg.get("mean_token_saving_rate_proxy")
    if saving is None:
        return None, None, None, "missing"
    return (
        float(saving),
        agg.get("mean_jaccard_proxy"),
        poc.get("case_count"),
        source,
    )


def _customer_raw_from_roi(roi: dict[str, Any], root: Path) -> tuple[float | None, float | None, int | None, str]:
    """Prefer documented customer-masked PoC over ROI rehearsal aggregate."""
    if CUSTOMER_PROXY_POC.is_file():
        out = _aggregate_from_poc(CUSTOMER_PROXY_POC, "customer_proxy_poc_ssot")
        if out[0] is not None:
            return out

    poc_rel = roi.get("poc_report_path")
    if poc_rel:
        poc_path = root / str(poc_rel).replace("\\", "/")
        if poc_path.is_file() and not any(m in str(poc_rel).lower() for m in REHEARSAL_MARKERS):
            out = _aggregate_from_poc(poc_path, "customer_poc_report.aggregate")
            if out[0] is not None:
                return out

    dual = roi.get("raw_repair_dual_report") or {}
    raw_block = dual.get("raw") or {}
    raw_saving = raw_block.get("mean_token_saving_rate_proxy")
    if raw_saving is not None:
        return (
            float(raw_saving),
            raw_block.get("mean_jaccard_proxy"),
            raw_block.get("rows"),
            "raw_repair_dual_report.raw",
        )

    proxy = roi.get("measured_proxy") or {}
    saving = proxy.get("mean_token_saving_rate_proxy")
    if saving is not None:
        return (
            float(saving),
            proxy.get("mean_jaccard_proxy"),
            proxy.get("case_count"),
            "measured_proxy",
        )
    return None, None, None, "missing"


def build() -> dict[str, Any]:
    signoff = _load(SIGNOFF)
    roi = _load(ROI)
    launch = _load(LAUNCH)
    edge = _load(EDGE)
    intake = _load(INTAKE)
    saving, jaccard_for_display, raw_rows, saving_source = _customer_raw_from_roi(roi, ROOT)
    saving_pct = f"{100 * float(saving):.1f}%" if saving is not None else "—"
    proxy = roi.get("measured_proxy") or {}
    launch_summary = launch.get("summary") or {}

    doc: dict[str, Any] = {
        "schema": "hybrid_b2b_commercialization_pipeline_v1",
        "generated_at_utc": _utc(),
        "labels": ["DRAFT", "internal_only", "research_only", "publish_allowed=false"],
        "product_model": {
            "summary_ko": "범용 SaaS가 아닌 하이브리드 B2B 공급망 파이프라인",
            "summary_en": "Hybrid B2B supply-chain pipeline — not generic multi-tenant SaaS",
            "github_role_ko": "클라이언트 Edge SDK/전처리기만 노출 — 마스터 코드북·디코더 OSS 금지",
            "revenue_axes": [
                "custom_codebook_build_fee",
                "usage_metering_per_traffic",
            ],
            "fail_comp_004": "Compression % and coord_wire token proxy must not merge in headlines or billing.",
        },
        "send_gate": signoff.get("send_gate", "HOLD"),
        "ready_for_external_send": bool(signoff.get("ready_for_external_send")),
        "counsel_signoff": bool(signoff.get("counsel_signoff")),
        "readiness_all_ok": bool(launch_summary.get("readiness_all_ok")),
        "launch_checklist": {
            "pass_count": launch_summary.get("pass_count"),
            "total": launch_summary.get("total"),
            "decision": launch_summary.get("decision"),
            "note_ko": "9/9 PASS는 오픈벤치·바인딩 확인이지 paid API GO가 아님",
            "artifact": _rel(LAUNCH),
        },
        "github_funnel": {
            "expose_only": [
                "edge_encoder_sdk_preprocessor",
                "coord_spec_extraction_client",
            ],
            "forbidden_oss": [
                "master_codebook",
                "tenant_decoder_internals",
                "FAIL-COMP-004 metric merge",
            ],
            "security_shield": {
                "retain_original_locally": True,
                "original_bulk_sent": False,
                "contract_pointer": _rel(ROOT / "docs/final/EDGE_ENCODER_SPEC_DRAFT_V1.md"),
                "maturity": edge.get("maturity", "sdk_alpha"),
            },
            "free_tier_viral": {
                "status": "HYPO",
                "compression_saving_range_hypothesis": "20-40%",
                "note_ko": "GTM 초안만 — 가격·SKU·GitHub 배포 SSOT 없음",
            },
        },
        "lanes": {
            "compression_api": {
                "sku": "MKM-COMPRESSION-B2B",
                "stages": [
                    {
                        "stage": 1,
                        "name": "client_coord_not_applicable",
                        "note_ko": "압축 레인은 GitHub Edge가 아닌 마스킹 JSONL·API 스텁 경로",
                        "maturity": "pilot_intake",
                    },
                    {
                        "stage": 2,
                        "name": "sandbox_pilot_day_1_90",
                        "driver": "masked_jsonl_proxy",
                        "customer_measured_raw_saving": saving_pct,
                        "customer_measured_raw_source": saving_source,
                        "customer_measured_poc_ssot": _rel(CUSTOMER_PROXY_POC)
                        if CUSTOMER_PROXY_POC.is_file()
                        else None,
                        "customer_measured_jaccard": jaccard_for_display,
                        "rows": raw_rows,
                        "rehearsal_proxy_note": (
                            "measured_proxy may differ — headline uses customer PoC aggregate when present"
                            if saving is not None
                            and proxy.get("mean_token_saving_rate_proxy") is not None
                            and abs(float(proxy["mean_token_saving_rate_proxy"]) - float(saving)) > 0.01
                            else None
                        ),
                        "ssot": _rel(ROOT / "docs/final/artifacts/compression_b2b_pilot_onepager_v1.md"),
                        "forbidden_headline": "Track A ~47% as customer SLA",
                    },
                    {
                        "stage": "3A",
                        "name": "core_decoder_metering",
                        "driver": "stateless_compression_api_stub",
                        "billing": "usage_metering",
                        "gate_note_ko": "readiness_all_ok 및 counsel_signoff 전 유료 청구선 잠금",
                        "artifacts": [
                            _rel(ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"),
                            _rel(WORKFLOW),
                        ],
                    },
                ],
            },
            "edge_sku_coord": {
                "sku": "SKU-COORD",
                "stages": [
                    {
                        "stage": 1,
                        "name": "github_edge_sdk",
                        "driver": "client_local_coord_extract",
                        "maturity": edge.get("maturity", "sdk_alpha"),
                        "retain_original_locally": edge.get("client_obligations", {}).get(
                            "retain_original_locally", True
                        ),
                        "ssot": _rel(EDGE),
                    },
                    {
                        "stage": 2,
                        "name": "vpc_air_gap_pilot",
                        "driver": "tenant_coord_wire_ingest",
                        "note_ko": "압축 JSONL 파일럿과 별도 계약·별도 실측",
                        "invoke": "scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1",
                    },
                    {
                        "stage": "3B",
                        "name": "private_decoder_custom_build",
                        "driver": "coord_wire_decode_on_private_infra",
                        "token_proxy_cl100k_reference": edge.get("coord_wire_schema", {}).get(
                            "token_proxy_cl100k_reference"
                        ),
                        "pilot_fixture": "rib55",
                        "billing": "custom_codebook_build_plus_metering",
                        "fail_comp_004": "Do not cite ~156 tok as compression API saving %",
                    },
                ],
            },
        },
        "unlock_protocol": {
            "name": "infra_smoke_open_bench_binding_check",
            "not_this": "paid_revenue_go_or_auto_enqueue",
            "steps": [
                {
                    "order": 1,
                    "id": "tenant_masked_jsonl_intake",
                    "action_ko": "B2B 테넌트 마스킹 JSONL 30건 입고·실측 정합",
                    "command": "py scripts/run_compression_pilot_roi_chain_v1.py --tenant-id <TENANT>",
                    "unlocks": "customer_measured_sla_numbers_only",
                },
                {
                    "order": 2,
                    "id": "vps_nginx_human_bind",
                    "action_ko": "a-codeai.com 정적 랜딩 + 압축 스텁(8010) 수동 nginx 바인딩 — 인프라 스모크",
                    "human_gate": True,
                    "unlocks": "open_bench_runtime_binding_verify",
                    "not_this": "billing_activation",
                },
                {
                    "order": 3,
                    "id": "patient_intake_internal_poc",
                    "action_ko": "원내 PoC 창 — 대외 SEND 아님",
                    "command": "py scripts/check_patient_intake_send_gate_v1.py --confirm-internal-poc",
                    "prereq": "public_facing_v17_reviewed",
                    "parallel_ok": True,
                },
            ],
        },
        "gate_snapshots": {
            "compression_legal_send": _rel(SIGNOFF),
            "edge_encoder": _rel(EDGE),
            "patient_intake": _rel(INTAKE),
            "compression_workflow": _rel(WORKFLOW),
        },
        "reproduce": {
            "build": "py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py",
            "compression_verify": "py scripts/run_compression_proof_completion_chain_v1.py",
            "edge_verify": "pytest tests/test_edge_encoder_sdk_v1.py -q",
        },
    }
    return doc


def render_md(doc: dict[str, Any]) -> str:
    comp = doc["lanes"]["compression_api"]
    edge_lane = doc["lanes"]["edge_sku_coord"]
    s2 = comp["stages"][1]
    proto = doc["unlock_protocol"]
    free = doc["github_funnel"]["free_tier_viral"]
    launch = doc["launch_checklist"]

    return f"""---
schema: hybrid_b2b_commercialization_pipeline_v1
tier: B-track Enterprise · internal ops briefing
labels: [DRAFT, research_only, publish_allowed=false]
send_gate: {doc.get("send_gate", "HOLD")}
---

# 하이브리드 B2B 공급망 상용화 파이프라인 (Fact-Lock)

**상태:** `send_gate: {doc.get("send_gate")}` · `ready_for_external_send: {doc.get("ready_for_external_send")}` · `counsel_signoff: {doc.get("counsel_signoff")}` · `readiness_all_ok: {doc.get("readiness_all_ok")}`

**제품 모델:** 범용 SaaS가 아니라 **하이브리드 B2B 공급망**. GitHub는 **Edge 전처리(미끼·보안 실드)** 만; 매출은 **닫힌 배관(커스텀 코드북 + 미터링)**.

머신 SSOT: `docs/final/artifacts/hybrid_b2b_commercialization_pipeline_v1_latest.json`

## 1. GitHub 실전 용도 (Funnel · 보안 실드)

| 용도 | 내용 |
| --- | --- |
| **노출 허용** | Edge SDK / Pre-processor · coord 스펙 추출 클라이언트만 |
| **금지** | 마스터 코드북·테넌트 디코더 OSS · FAIL-COMP-004 합선 |
| **보안 실드** | `retain_original_locally: true` · bulk 미전송 — 엔터프라이즈 검증용 설계 계약 (`maturity: sdk_alpha`) |
| **Free-Tier 바이럴** | **`[HYPO]`** {free.get("compression_saving_range_hypothesis", "20-40%")} — GTM 초안만, 가격 SSOT 없음 |

## 2. 레인 분리 배관도 (FAIL-COMP-004)

**압축 API 레인**과 **Edge SKU-COORD 레인**은 **순차 1→2→3 한 줄이 아님**. 아래 **3A / 3B**를 합치지 말 것.

### Compression API (`MKM-COMPRESSION-B2B`)

| 단계 | 구동 | SSOT |
| --- | --- | --- |
| 파일럿 | 마스킹 JSONL proxy · Day 1~90 · raw **{s2.get("customer_measured_raw_saving", "—")}** ({s2.get("rows", "—")} rows) | `compression_b2b_pilot_onepager_v1.md` |
| **3A** | 공용 stateless API + **Usage Metering** | `compression_b2b_recommended_workflow_v1.json` |
| 금지 헤드라인 | Track A ~47%를 고객 SLA로 쓰지 않음 | FAIL-COMP-004 |

### Edge SKU-COORD (별도 SKU)

| 단계 | 구동 | SSOT |
| --- | --- | --- |
| 1 | GitHub Edge SDK · 로컬 coord 추출 | `edge_encoder_spec_v1_latest.json` |
| 2 | VPC/air-gap 파일럿 | `Invoke-EdgeEncoderAirGapPoC_v1.ps1` |
| **3B** | 전용 디코더 · rib55 PoC **~156 tok** 참조 | coord wire — **압축 %와 합산 금지** |

## 3. Launch checklist (오픈벤치 ≠ 과금 GO)

- Checklist: **{launch.get("pass_count")}/{launch.get("total")}** `{launch.get("decision")}`
- **`readiness_all_ok: {doc.get("readiness_all_ok")}`** — nginx 바인딩·스모크 확인용; 유료 API 청구 해제 아님

## 4. 인프라 스모크 · 오픈벤치 바인딩 확인 프로토콜

이름: **`{proto.get("name")}`** — `{proto.get("not_this")}`

| 순서 | 액션 | 비고 |
| --- | --- | --- |
| 1 | 테넌트 마스킹 JSONL 30건 입고·실측 | `run_compression_pilot_roi_chain_v1.py --tenant-id <TENANT>` |
| 2 | VPS nginx 수동 바인딩 (a-codeai 랜딩 + :8010 스텁) | Human gate · 과금 GO 아님 |
| 3 | intake 내부 PoC (`--confirm-internal-poc`) | v1.7 카피 검토 · 대외 SEND 별도 |

## 5. 결론

GitHub = 신뢰용 인코더(Edge) 미끼. Compression **3A** 매출 = 커스텀 샤드·미터링. Edge **3B** = 별도 VPC/디코더 계약. **대외 SEND·유료 청구는 지휘관+counsel sign-off 전 HOLD.**

**재현:** `py scripts/build_hybrid_b2b_commercialization_pipeline_v1.py`
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    doc = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.json_only:
        OUT_MD.write_text(render_md(doc), encoding="utf-8")
    print(f"Wrote {_rel(OUT_JSON)}")
    if not args.json_only:
        print(f"Wrote {_rel(OUT_MD)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
