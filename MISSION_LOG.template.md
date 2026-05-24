# MISSION_LOG — 운영 체크리스트 (디스크 앵커)

**사용법**: 로컬 전용 파일 `MISSION_LOG.md`를 쓴다 (저장소 루트,`.gitignore`로 비추적). 이 템플릿을 복사해 시작한다.

**파일 비대 시 (2026-05-23):** `py scripts/split_mission_log_old_v1.py` — **작전 보드·운영 일정 SSOT만** `MISSION_LOG.md`에 두고, 나머지는 `MISSION_LOG.old.md`(참고·비-SSOT). 백업: `MISSION_LOG.pre_split_backup.md`.

**역할 분리**: 작전 스냅샷·핸드오프 문단은 `docs/final/CURRENT_OPS_SNAPSHOT.md`에 두고, 본 파일은 **로컬 체크리스트·exit 조건**만 기록한다. 동일 SSOT를 스냅샷과 이중 서술하지 않는다(루트 `.cursorrules`·`AGENTS.md`와 동일 방향).

**병렬 세션**: Agents Window 등에서 동시에 `MISSION_LOG.md`를 쓰면 파일 경합이 날 수 있으니, 한 번에 한 에이전트(또는 한 채팅)만 이 파일을 갱신하는 것을 권장한다.

**에이전트 주도 (권장):** 메인 에이전트가 `MISSION_LOG.md`를 **생성·갱신**하고, 임무를 쪼개 **서브에이전트**(`Task` 등)에 파견한 뒤 결과를 **Evidence·Completed**로 수합한다. 지휘관은 **방향·고위험 승인·STOP**만 주면 된다(매 스텝 `OK` 필수 아님). 서브 세션은 본 파일을 수정하지 않는다.

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

## Ops lane — 관리 전용 채팅 (개발 채팅과 분리, 선택)

**목적:** 채팅 하나를 **Cursor·Windows·스케줄·보안 위생** 전용으로 두고, 피처·버그·리뷰는 **다른 채팅**에서만 진행하면 컨텍스트가 분리된다.

| 구분 | 관리 채팅에서 다룸 | 개발 채팅에 두지 않음(권장) |
|------|---------------------|-----------------------------|
| Cursor / IDE | `.vscode/settings.json`, `tasks.json`, `keybindings.json`; `.cursor/rules`, `hooks.json` (레포에 둘 때는 PR·커밋 범위를 작게) | 동일 PR에 대형 코드 변경과 섞지 않기 |
| 스케줄 | `schtasks`, `scripts/Register-*Task.ps1`, `Invoke-MkmPersonaHealth_v1.ps1` 페르소나 (`AGENTS.md` 「페르소나 단축 호출」) | |
| 보안·거버넌스 | `Invoke-AmsaengEosaGovernanceCycle.ps1`, `Invoke-SafeOpsSurfaceCheck.ps1`, `Show-RemotePublicationMode.ps1` — **절차·exit·산출 경로만** | API 키·웹훅 URL·`.env` 내용·비밀 평문 채팅·커밋 **금지** |
| 비밀 | User 환경 변수, 루트 `.env`(비추적), `LOCAL_VS_VPS`·`Invoke-MkmSecretsHybridReadiness_v1.ps1` 런북만 안내 | 값 붙여넣기 금지 |

**개발 채팅으로 넘길 때:** 관리 채팅에서 확정한 **한 줄 DoD + 변경 경로**만 복붙한다.

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

## Automation Frontline — 일간·주간 (고정 2줄 + 선택 1줄)

**역할:** 기계 영역은 **계산·검증·`*_latest.json` 산출**까지. 실행 스위치·도장·커밋·푸시·실매매는 **인간 성역**(산출물만으로 자동 연결되지 않음). 상세 트리거 표는 루트 `AGENTS.md` 「페르소나 단축 호출」.

**저장소 루트 `C:\workspace`에서 실행(Windows).** 완료 시 Active 표 또는 아래 Evidence에 **exit 0 한 줄**을 남긴다.

| 리듬 | 한 줄 (복사) | Evidence (예시) |
|------|----------------|------------------|
| **일간** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AmsaengHealth` | 터미널 exit 0 · 헬스 로그에 `overall_ok` 등(해당 스크립트 출력) |
| **주간** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` | exit 0 · `run_fact_lock_bundle.ps1`에 포함된 pytest·게이트 범위는 `AGENTS.md`·`MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단 |
| **선택(초경량)** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona P0` | `scripts\verify_p0_constitution_gate_paths.ps1` exit 0 |

**연속(이미 등록한 PC):** Task Scheduler 작업 `\MKM-Trading-Automation-Health-30min`은 `scripts\Register-TradingAutomationHealthTask.ps1` 기본값으로 **`scripts\Run-TradingAutomationHealthTask.ps1`**를 주기 실행한다. 수동 1회: `schtasks /Run /TN "\MKM-Trading-Automation-Health-30min"`. 일간 한 줄과 **중복이면** 지휘관 PC 부하에 맞게 하나만 유지해도 된다.

**Completed 규칙:** 위 리듬 행을 돌린 날짜·exit 0를 **Completed**에 한 줄 남기거나, Active 표의 해당 행 Evidence만 갱신한다(스냅샷·CENTRAL과 동일 문단 이중 기술 금지).

### 서브에이전트 복붙 브리프 (메인 채팅이 MISSION_LOG 소유)

**메인이 브리프 문안을 생성**해 서브 첫 메시지에 붙여도 된다. **서브는 `MISSION_LOG.md`를 수정하지 않는다.**

1. **범위:** (디렉터리 또는 브랜치 한 줄, 예: `scripts/…`만 / `tests/…`만)
2. **금지:** `MISSION_LOG.md`·`docs/final/CURRENT_OPS_SNAPSHOT.md`·`docs/final/CENTRAL_AGENT_MEMORY_V1.md`·실매매·`git push`·비밀 커밋
3. **DoD:** (exit 0 명령 한 줄, 예: `py -m pytest tests/test_….py -q`)
4. **증거:** (산출 경로 또는 로그 한 줄)
5. **완료 후:** 메인 채팅에 **diff 요약 + DoD 달성 여부**만 보고(메인이 MISSION_LOG·승인 게이트 갱신)

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
