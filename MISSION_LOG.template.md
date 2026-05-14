# MISSION_LOG — 운영 체크리스트 (디스크 앵커)

**사용법**: 로컬 전용 파일 `MISSION_LOG.md`를 쓴다 (저장소 루트,`.gitignore`로 비추적). 이 템플릿을 복사해 시작한다.

**역할 분리**: 작전 스냅샷·핸드오프 문단은 `docs/final/CURRENT_OPS_SNAPSHOT.md`에 두고, 본 파일은 **로컬 체크리스트·exit 조건**만 기록한다. 동일 SSOT를 스냅샷과 이중 서술하지 않는다(루트 `.cursorrules`·`AGENTS.md`와 동일 방향).

**병렬 세션**: Agents Window 등에서 동시에 `MISSION_LOG.md`를 쓰면 파일 경합이 날 수 있으니, 한 번에 한 에이전트(또는 한 채팅)만 이 파일을 갱신하는 것을 권장한다.

## 채팅창 작업일정 앵커 (에이전트 고정 · SSOT)

| 대상 | 파일 | 금지 |
|------|------|------|
| **임무·MISSION·다단계 Phase 체크리스트·채팅창 일정** | 루트 **`MISSION_LOG.md`** (본 템플릿에서 복사) | `reports/daily_thread_work_*.md`를 **일정 본문 앵커**로 쓰지 않음 |
| **Ops 한 줄·「일기 반영」** | `reports/daily_thread_work_YYYY-MM-DD.md` + `athena_daily_thread_log_sync_v1.py` | MISSION_LOG와 **동일 표 이중 기술** 금지(역할 분리) |
| **일시 핸드오프 문단** | `docs/final/CURRENT_OPS_SNAPSHOT.md` | MISSION_LOG·스냅샷 **이중 서술** 금지(루트 `.cursorrules`·`AGENTS.md` 동일) |
| **장기 정체성·분기 한 줄** | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` | **일정 표·Phase 체크리스트 전체**를 CENTRAL에 올리지 않음 |
| **옵시디언** | 개인 볼트(선택) | 레포 SSOT·에이전트 장기기억으로 **자동 승격 없음** |

PowerShell 예: `Copy-Item -Path MISSION_LOG.template.md -Destination MISSION_LOG.md`

**역할:** 세션마다 리셋되는 채팅 UI 대신, **동일 지휘관 PC의 디스크**에서 크로스 채팅 **임무·종료 조건·작업일정(표)**를 맞춘다. 구현 경로·게이트 순서의 SSOT는 `docs/final/P0_COMMERCIALIZATION_TRACKER.md`, 구현 팩트는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`이다.

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

## Autonomous evolution loop (draft v1)

**정의**: [측정 → 제안 → 검증 → 결정]의 **유한** 루프. 무한 최적화·무승인 커밋·이론 상수 임의 변경 **금지**.

| Step | 내용 | 레포 앵커 |
|------|------|-----------|
| 1 Snapshot | 벤치 연동 KPI 스냅샷 | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` 등 |
| 2 Proposal | 가설·패치는 **allowlist + 인간 게이트** 없으면 스킵 | 초안: `scripts/run_autonomous_evolution_loop_draft_v1.py` (`--dry-run` 기본) |
| 3 Validation | `pytest` / `verify_p0` 등 **한 줄 gate**, 타임아웃 필수 | `--gate-profile minimal` (권장) 또는 `--gate-cmd "..."`, `--gate-timeout` |
| 4 Decision | 산출 JSON만; **고착(Commit)은 지휘관 또는 CI 정책** | `docs/final/artifacts/autonomous_evolution_loop_draft_v1_latest.json` |

**한 줄 실행 (권장 — 스냅샷 + 소형 게이트):** `py scripts/run_autonomous_evolution_loop_draft_v1.py --gate-profile minimal`  
**한 줄 실행 (게이트 생략):** `py scripts/run_autonomous_evolution_loop_draft_v1.py --gate-profile none`  
**회귀:** `py -m pytest tests/test_autonomous_evolution_loop_draft_smoke.py -q` (파일 내 `minimal` 게이트 테스트 포함; `minimal` 프로파일 자체는 AE 단일 노드 + shadow만 호출해 재귀 방지)

## Completed (선택 아카이브)

- (완료된 행은 여기로 옮기거나 날짜만 남김)
