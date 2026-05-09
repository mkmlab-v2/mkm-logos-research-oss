# 한의 원전·코호트 인제스트 — 인수인계 (Fact-Lock)

**작성일**: 2026-03-28 · **레포 반영**: 2026-05-10  
**역할**: 라벨 코호트 **A** vs 원전·Proxy 말뭉치 **B**의 **격벽**을 문서 SSOT로 고정한다. 구현 체인의 세부 경로는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 호출 가능 스크립트가 우선이다.

## 1. A/B 분리 (반드시)

| 구분 | 용도 | 금지 |
|------|------|------|
| **A** | 프로젝트 규칙에 따른 라벨·코호트, 본선 게이트에서 허용된 평가 | — |
| **B** | 한의 원전·Proxy·연구 말뭉치, NotebookLM B 트랙 등 | 본선 분류·204 OOF·실매매·프로덕션 트리거와 **자동 합선 금지** |

## 2. 교차 참조 (단일 근거로 삼지 말 것)

- `docs/NotebookLM_sources_manifest.md` — `## 이제마_B_Track`
- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 관련 절·표
- 의사 CDS **보조 출력 봉투**(별도 제품 계약): `docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json` — 임상 최종판단 대체 아님

## 3. 상태

원전 인제스트 **자동 파이프라인 전체**가 본 문서에 고정되지는 않는다. 경로·게이트 판정은 매 실행 SSOT(`CONSTITUTION`·`.py`·exit code)를 따른다.
