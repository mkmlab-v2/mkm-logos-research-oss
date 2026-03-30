# CLAUDE.md — Cursor/Claude용 마스터 컨텍스트 (슬림)

**목적**: 세션 초기에 **한 화면**으로 방향을 맞춘다. 장문 가이드는 각 규칙·문서에 둔다.

## 에이전트 동작

- **TITAN**: 루트 `.cursorrules` 최상단 — 자율 기동, **이항 선택([A]/[B]) 강요 금지**, 고위험만 승인 요청.
- **중앙 지휘부 규칙**: `.cursor/rules/sovereign-central-command.mdc` (`alwaysApply`).
- **코드/추론 “구현 여부”**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 를 호출 가능한 `.py`와 대조한다. **Multi-Lens·TOE 비단정**은 동 문서 §1.1.

## 환경

- **경로**: `C:/workspace`
- **Python**: Windows에서는 `py` 사용(프로젝트 규칙과 동일).

## 더 읽을 때

- 상용화·작업 순서: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (해당 작업 시).
- 에이전트 역할 요약: 루트 `AGENTS.md`.
