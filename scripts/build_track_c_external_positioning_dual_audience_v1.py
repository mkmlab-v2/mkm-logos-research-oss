#!/usr/bin/env python3
"""Build dual-audience external positioning one-pager (B2B primary · academic secondary)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/track_c_external_positioning_dual_audience_v1_latest.md"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_stats() -> dict[str, Any]:
    doc = _load(BUNDLE)
    gf = doc.get("graph_files") if isinstance(doc.get("graph_files"), dict) else {}
    ms = doc.get("manifest_snapshot") if isinstance(doc.get("manifest_snapshot"), dict) else {}
    align = doc.get("alignment") if isinstance(doc.get("alignment"), dict) else {}
    return {
        "verse_count": ms.get("corpus_verse_count", "—"),
        "nodes": gf.get("nodes_line_count", "—"),
        "edges": gf.get("edges_line_count", "—"),
        "graph_refs": align.get("graph_verse_ref_distinct_count", "—"),
    }


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = _bundle_stats()
    body = f"""# Track C — 대외 포지셔닝 1페이지 (이중 청중 · Fact-Lock)

- **generated_at_utc:** `{ts}`
- **schema:** `track_c_external_positioning_dual_audience_v1`
- **status:** `DRAFT_AUTO` — **법무 검토 전 대외 발송 금지**
- **aligned_with:** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.0a · §3.6 · §3.8 · §9 · `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7
- **GTM 1파도:** B2B 매크로·리스크 (본 문서 **Section A**) · 학술/신학 권위전 **아님** (Section B = 방법론·재현 패키지만)

> **운영 메모:** 과거 LG HS 등 **종료된 사업선**은 대외·내부 GTM SSOT에 **포함하지 않음**. 본 문서는 Track C 현행 파도만 기술.

---

## 측정 가능 팩트 (대외·내부 공통 — 과장 금지)

| 항목 | SSOT 스냅샷 | 비고 |
|------|-------------|------|
| 정경 구절 수 | **{s["verse_count"]}** | `logos_corpus_manifest_v1_latest.json` |
| 원어 아톰(마스터 요약) | **41,658** | `original_language_master_atoms_summary_latest.json` |
| 의미 그래프 엣지(승인본) | **{s["edges"]}** | `logos_corpus_graph_bundle_v1_latest.json` |
| 그래프 노드 / 커버 구절 ref | **{s["nodes"]} / {s["graph_refs"]}** | 전 구절 full-graph **아님** |
| 이론 pairspace 상한 | **~4.8×10⁸** | 질의 시 전량 평가 **없음** · `[HYPO]` |
| Logos 렌즈 | **`[NON_GATING]`** | 실매매·최종 트리거 **직접 연결 금지** |
| 단일 TOE·“역사상 1위” | **금지** | `CONSTITUTION §1.1` · `PUBLIC_FACING` §3 |

---

## MKM OS Application Ladder (GTM Framework)

**정체성:** 예언가·컨설턴트·지배구조 설계자가 **아님**. 고문헌 패턴(Logos)과 현실 노이즈(Field)를 겹쳐 **확률적 궤적·posture**를 **아티팩트로 렌더링하는 관측기**.

```text
[MKM OS Application Ladder (GTM Framework)]
1. Core (Showroom): 고문헌(Logos) 멀티렌즈 + Field 정제 → 아티팩트 기반 투명성 관측 (Magic Orb / mkmlife · jemaai.cloud)
2. Cash Spearhead 1: B2B 매크로 레짐 경보 및 실물 자본 방어 Posture (MDD **관측** — 매매·자문 아님)
3. Cash Spearhead 2 (Next): General Prophecy / 사회·제도 신뢰 스트레스 관측 및 Pre-News 레일 ([HYPO] · B-rail)
```

**SSOT 교차:** `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.1 · §3.5 · §3.6 · §3.8 · `GENERAL_PROPHECY_SCHEMA_V1.json`

### Fact-Lock · Final Action (영구)

- **Final Action: HOLD** — 본 Ladder는 **Track A·실매매·상용 승격 GO를 의미하지 않음**.
- **Logos `[NON_GATING]`** — Logos **단독** 예언·종말/붕괴 **결정론 단정 금지**; 최종 posture는 **1차 Field(`regime_map`) + 운영 게이트 + HITL**.
- **Track A·실매매 자동 합선 금지** — B-track `[HYPO]`·`general_prophecy`·Pre-News shadow → 본선 주문·게이트웨이 트리거 **물리 분리** (`CONSTITUTION` track_wall).
- **GTM 제외 (대외 창끝 아님):** 지정학 분쟁 **예측** · 기업 지배구조 **설계/자문** — 재현 JSON·면책·채점 SSOT 부족; 연구만 병렬 시 `[HYPO]` 격리.

---

# Section A — B2B (CEO · CRO · 전략/리스크) **← Cash Spearhead 1**

## 한 줄

**거시·레짐(Field) 중심의 조기 경보·시나리오 포즈** — 재현 가능 JSON·감사 로그·운영자(HITL) 전제. **투자자문·매매 지시·수익 보장 아님.**

## 제공 (예시)

- 분기/월간 **매크로·레짐 브리프** (PDF / 링크)
- **경보·포즈 라벨** (HOLD / REDUCE / WATCH 등 — **buy/sell 아님**)
- (옵션) 읽기 전용 경보 API — `docs/final/openapi_macro_risk_warning_api_v1.yaml`
- (프리미엄) **고전 코퍼스 스트레스 테스트 내러티브** — `track_c_b2b_logos_lens_appendix_v1_latest.md` · `[NON_GATING]`

## 제공하지 않음

- 알파·목표가·자동 매매·펀드 운용 대행
- 고객 거래소 API·실키 저장/중계
- 핵심 산식·가중치·전체 추론 그래프 공개

## 비교 포지션 (Fact-Lock)

- **WRING류:** 기초모델 표현공간 교정(기초과학)
- **MKM Track C:** **운영 파이프라인·정책 바인딩·감사 추적** (응용 거버넌스)
- **우열 단정 금지** — “통제 가능·증거로 재현 가능”만 주장

## Short copy (EN · §9 default)

> MKM provides a governance-driven risk warning and scenario posture service that integrates multi-lens analytics. The service supports exposure-control decisions with reproducible artifacts and verification logs. It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.

## 근거·데모

- 세일즈 시트: `track_c_b2b_macro_alert_offer_onepager_latest.md`
- MVP: `track_c_2026_h2_macro_risk_alert_report_mvp_v1.md`
- 쇼룸(관측): `https://jemaai.cloud` — Topology / Trust viz · **자동 매매 트리거 없음**

---

# Section B — 학술 · 데이터사이언스 · 디지털 휴먼ities **← Core 방법론 · 병렬 (Cash 2순위 아님)**

## 한 줄

**31k 구절 코퍼스 + 아티팩트 바인딩 멀티렌즈 관측 프레임**의 **재현 가능 방법론·벤치 패키지** — “역사상 최초·1위·실시간 full-graph” **주장 금지**.

## 제안 가치 (학술용)

- **코퍼스·그래프·벡터 정책** 스냅샷 + JSON Schema · pytest 회귀 경로 공개(계약 범위)
- **렌즈 격벽** 문서화: Field → 사상/명리/Logos(`[NON_GATING]`) → Conflict → Posture
- **반증·신선도·품질** sidecar (예: falsification benchmark, freshness sidecar)
- **한계 명시:** meaning graph **{s["edges"]}** 엣지 · **{s["graph_refs"]}** ref 커버 · pairspace는 **이론 상한**

## 학술용 금지 (peer review 리스크)

- “인류 역사상 성경 활용 1위” · “단일 통일 이론 완성” · “실시간 4.8억 쌍 연산”
- Logos를 **가격·종말·거시 붕괴의 결정론적 예언**으로 서술
- B-track `[HYPO]` 산출을 Track A·실증 논문 **결과**처럼 제출

## Short copy (학술 abstract 초안)

> We describe an artifact-governed, multi-lens observability framework over a {s["verse_count"]}-verse corpus with explicit non-gating isolation for classical-text narrative layers. Reported graph statistics reflect approved meaning edges (n={s["edges"]}), not full-corpus realtime search. The system does not claim theological authority, investment performance, or completion of a unified physical theory.

## 근거 패키지 (내부/NDA)

- `logos_corpus_graph_bundle_v1_latest.json` · `logos_insight_bundle_v1_latest.json`
- `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (Logos Track B 표)
- 쇼룸 thin slice: `public_showroom_logos_research_v1.html` · `[HYPO]` / `research_only`

---

## 공통 면책 (KO · footer paste)

본 자료는 정보 제공·의사결정 보조 목적입니다. 투자자문·매수/매도 권유·수익·임상 효능을 보장하지 않습니다. 고전 텍스트·렌즈 내러티브는 **`[NON_GATING]`** 해석층이며 최종 조치는 **1차 실물 레짐·운영 게이트·운영자**가 확정합니다.

---

## 재생성

```bash
py scripts/build_track_c_external_positioning_dual_audience_v1.py
```

**Related SSOT:** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.0a · `track_c_combined_b2b_offer_onepager_v1_latest.md` · `build_track_c_b2b_meeting_pack_v1.py`
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
