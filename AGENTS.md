# AGENTS — 워크스페이스 에이전트 SSOT 포인터

**역할**: Cursor/Athena 에이전트가 먼저 읽는 **짧은 진입점**이다. 상세 규칙은 아래 파일이 주도한다.

## 필수 우선순위

1. **루트 `.cursorrules`** — 최상단 **TITAN · 자율 기동(Command-by-Negation)**. 예외가 아니면 권장 조치를 질문 없이 수행·사후 보고; 끝맺음은 [A]/[B] 선택 강요 없이 **완료 보고 + 잔여 리스크(있을 때만)**.
2. **`.cursor/rules/sovereign-central-command.mdc`** — Vault·NotebookLM·보안·운영(3문장 요약 + **§4 마무리**). §4에서 **폐지**: “Next Action 2가지”, `[A]`/`[B]`·a/b 강요. **대체**: TITAN 마무리 또는 고위험 시 **승인 범위만** 명시(루트 `.cursorrules`와 동일 방향).
3. **구현 팩트(환각 차단)**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 기획·NotebookLM만 보고 “이미 구현” 단정 금지.

## 도메인 핸드오프(참고)

- 한의 원전·코호트: `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` (라벨 A vs 원전 B 혼선 금지).
- NotebookLM 소스: `docs/NotebookLM_sources_manifest.md`.

## 경로

- 작업 루트: `C:/workspace` (Windows). Python 실행은 `py` 권장.
