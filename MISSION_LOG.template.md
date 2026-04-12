# MISSION_LOG — 운영 체크리스트 (디스크 앵커)

**사용법**: 로컬 전용 파일 `MISSION_LOG.md`를 쓴다 (저장소 루트,`.gitignore`로 비추적). 이 템플릿을 복사해 시작한다.

**역할 분리**: 작전 스냅샷·핸드오프 문단은 `docs/final/CURRENT_OPS_SNAPSHOT.md`에 두고, 본 파일은 **로컬 체크리스트·exit 조건**만 기록한다. 동일 SSOT를 스냅샷과 이중 서술하지 않는다(루트 `.cursorrules`·`AGENTS.md`와 동일 방향).

**병렬 세션**: Agents Window 등에서 동시에 `MISSION_LOG.md`를 쓰면 파일 경합이 날 수 있으니, 한 번에 한 에이전트(또는 한 채팅)만 이 파일을 갱신하는 것을 권장한다.

PowerShell 예: `Copy-Item -Path MISSION_LOG.template.md -Destination MISSION_LOG.md`

**역할**: 채팅 컨텍스트와 무관하게 **임무 단위 종료 조건**을 남긴다. 구현 경로·게이트 순서의 SSOT는 `docs/final/P0_COMMERCIALIZATION_TRACKER.md`, 구현 팩트는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`이다.

## Active

| ID | Mission (한 줄) | Exit condition (명령·파일) | Status |
|----|-----------------|----------------------------|--------|
| — | (비어 있음) | — | — |

## 한 줄 추가 시 (복사)

1. 위 표에 행 추가 또는 아래 체크리스트 사용.
2. 완료 시 **Evidence**에 exit 0 로그 한 줄 또는 산출 경로를 적는다.

## 체크리스트 템플릿

- [ ] **Mission:**
- [ ] **Exit:** (예) `py -m pytest tests/test_example.py -q` → exit 0
- [ ] **Evidence:** (예) 로그 / `docs/final/artifacts/...`

## Completed (선택 아카이브)

- (완료된 행은 여기로 옮기거나 날짜만 남김)
