# Copilot SDK + MCP (isolated experiment)

**목적:** GitHub Copilot SDK(프리뷰)로 **기존 레포 스크립트를 실행·exit code 해석**하는 래퍼만 실험한다.  
**금지:** `projects/bitcoin-trading/ops` 본선 트리 수정, `check-public-copy.ps1` 등 팩트 스크립트 본문 변경, 실매매·실키 경로.

## 원칙

- **실행:** 래퍼는 `pwsh`/`py`로 이미 존재하는 스크립트를 호출하고, stdout/stderr·exit code를 구조화해 보고한다.
- **승인:** SDK Approval Handler는 **지휘관 수동 컨펌 없이 다음 단계 진입 불가** 정책을 강제하는 차단막으로만 쓴다(권한 대행 아님).
- **Fact-Lock:** 판단 근거는 여전히 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`, 루트 `AGENTS.md` 등 디스크 SSOT.

## 상태

스켈레톤만 둔다. Node 의존성·SDK 버전은 지휘관 환경에 맞춰 `package.json`으로 고정 후 설치.

## 관련

- Hermes 얇은 프로필: `projects/bitcoin-trading/ops/.hermes.md`
- L2 마일스톤·도구 경계: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (L2 표)
- **JSON Schema + stdio MCP 표본(Python):** `../mcp-jsonschema-stdio/` — 본 폴더와 독립; Copilot SDK는 여기서 만든 MCP를 클라이언트로만 연결하는 실험에 쓸 수 있음
