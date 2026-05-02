# MKM AI — API Branding Bridge v1 (계약 비파괴)

**역할:** 브랜드·도메인 **서술**과 **OpenAPI/코드 계약 SSOT**를 분리한다. 본 파일은 마케팅·랜딩에서의 **이름·역할 정렬**만 고정하며, 스키마 복제나 신규 대외 스키마 명을 만들지 않는다.

**상위 SSOT:** `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.6, §11.1, `P0_COMMERCIALIZATION_TRACKER.md` L2.

## 도메인·역할 (요약)

| 표면 | 용도 (대외 서술) | 기술 메모 |
|------|------------------|-----------|
| `a-codeai.com` | B2B 압축·API 리드, `/v1` 분리형 엔드포인트 문맥 | 정적 랜딩과 API 프록시 분리 — `P0` nginx 예시 참조 |
| `jema-ai.com` | 브랜드 허브·설명 | no1kmedi 경로 SSOT는 별 문서 |
| `jemaai.cloud` | 공개 쇼룸·전광판형 체험 | 실매매 관제와 분리 (`AGENTS.md` 쇼룸 스펙) |

## 계약 SSOT (복제 금지 — 포인터만)

- 토큰 압축 스텁 v1: `docs/final/openapi_token_compression_stub_v1.yaml` + `scripts/compression_token_api_stub.py`
- 매크로 리스크 경고 API: `docs/final/openapi_macro_risk_warning_api_v1.yaml`, `docs/final/artifacts/macro_risk_warning_api_response_contract_v1.json`

**금지:** `mkm-ai-insight.v1` 등 신규 스키마 명을 OpenAPI·테스트·P0 게이트 반영 전에 대외 **확정명**으로 사용하지 않는다 (`TRACK_C` §11.1).

## 메시지 프레임

- Enterprise API add-on 문장은 `TRACK_C` §9 Enterprise API framing 과 동일 선상에서만 확장한다.
- 압축 제품: 무손실·무조건 복원 단정 금지 — `TRACK_C` §3.1.
