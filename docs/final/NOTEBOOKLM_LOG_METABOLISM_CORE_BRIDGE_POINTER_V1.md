# NOTEBOOKLM — LOG_METABOLISM ↔ CORE 인텔리전스 격벽 포인터 (v1)

**역할**: NotebookLM 노트 `MKM_CORE_INTELLIGENCE_V1`에만 소스로 붙이기 권장되는 **경로 포인터**. 구현·수치의 단일 진실은 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능한 스크립트·`docs/final/artifacts/*.json`이다.

## Fact-lock

- 구현 팩트 SSOT: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (LOG_METABOLISM·NL metabolism 관련 표).
- 본 문서는 **브리핑·소스 정렬**용이며, 예언 승격·본선 OOF·실매매 트리거와 **자동 합선되지 않는다** (`docs/NotebookLM_sources_manifest.md` A/B 이원).

## Refinery (로그 메타볼리즘) 레일

| 단계 | 경로 |
|------|------|
| JSONL 인제스트 | `scripts/ingest_notebooklm_metabolism_jsonl.py` |
| 소스 우선 스캔 | `scripts/discover_nl_metabolism_source.py` → `docs/final/artifacts/derived/notebooklm_pull_manifest_v1.json` |
| 합성 코호트 (스모크) | `scripts/generate_log_metabolism_synthetic_cohort_v1.py` |
| 명리 상관 입력 변환 | `scripts/convert_log_metabolism_to_myeongri_correlation_input_v1.py` |

## Vault · NotebookLM 소스 미러

- 매니페스트: `docs/NotebookLM_sources_manifest.md`
- 미러 실행: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`

## B-track 승격 산출물 (포인터만)

- 통찰↔게이트 링크 맵: `docs/final/artifacts/btrack_insight_promotion_bridge_index_v1_latest.json` (스코어 미주입·합선 없음)

증분 갱신만; NotebookLM 노트 **전체 wipe 금지** — 매니페스트 원칙과 동일.
