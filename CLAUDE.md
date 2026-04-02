# CLAUDE.md — Cursor/Claude용 마스터 컨텍스트 (슬림)

**목적**: 세션 초기에 **한 화면**으로 방향을 맞춘다. 장문 가이드는 각 규칙·문서에 둔다.

## 에이전트 동작

- **TITAN**: 루트 `.cursorrules` 최상단 — 자율 기동, **이항 선택([A]/[B]) 강요 금지**, 고위험만 승인 요청.
- **중앙 지휘부 규칙**: `.cursor/rules/sovereign-central-command.mdc` (`alwaysApply`).
- **코드/추론 “구현 여부”**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 를 호출 가능한 `.py`와 대조한다. **Multi-Lens·TOE 비단정**은 동 문서 §1.1.
- **12AI vs 코드북**: **12AI**는 Cursor 작업 라우팅용 오케스트레이션 라벨이며, 코드북 도메인·샤드 개수와 **1:1로 묶지 않는다.** (보통 복잡·고위험 작업만 2~4 전문 에이전트로 분산.) 상세: 루트 `AGENTS.md`, `.cursor/skills/auto-12ai-routing/SKILL.md`.

## 환경

- **경로**: `C:/workspace`
- **Python**: Windows에서는 `py` 사용(프로젝트 규칙과 동일).
- **공유 B-track SSOT(팩트 우선)**: `G:\공유 드라이브\MKM_DATA_VAULT\vault\btrack_artifacts_verified` — 로컬 산출물 동기화: `scripts/push_local_artifacts_to_vault.ps1`
- **어휘 계약**: `docs/final/MASTER_Linguistic_Contract_2026.md` — 외부 사전 수신: `scripts/setup/fetch_external_lexicons.ps1`, 승격: `scripts/push_external_lexicon_to_vault.ps1`

## 더 읽을 때

- 상용화·작업 순서: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (해당 작업 시).
- 에이전트 역할 요약: 루트 `AGENTS.md`.
- **Gemini MCP vs 배치 CLI 라우팅·비용 통제**: 루트 `AGENTS.md` 섹션 **「Gemini 멀티모달: MCP vs 배치 CLI」**.
