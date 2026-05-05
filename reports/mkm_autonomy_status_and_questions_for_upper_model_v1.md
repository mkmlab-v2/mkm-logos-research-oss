# MKM 무중단·자율 작업 — 현황 보고 및 상위 모델 질문서 (v1)

**작성 목적:** 상위/대형 모델에게 컨텍스트를 넘겨 병목 해소·운영 설계를 조언받기 위한 단일 패키지.  
**근거 범위:** 2026-05-03 기준 로컬 확인(작업 스케줄러, `mkm_orchestrator_audit.jsonl`, 스크립트 인자, `todo_queue_latest.json` 내용은 세션에서 확인; **NotebookLM·추측 수치는 미포함**).

**후속 운영 표준:** 상위 지휘 가이드라인을 반영한 규약 초안은 `docs/governance/mkm_operational_standard_v1.md` 를 참고한다.

---

## 1. 한 줄 요약

- **데몬은 동작 중:** `MKM_OrchestratorDaemon`(예: `run_mkm_continuous_daemon.ps1`, 인자 `-LoopSeconds 60 -MaxTasksPerInvocation 4 -HeavyEveryCycles 3`).
- **Track C 기계 큐(`todo_queue_v1`)는 동일 시점 기준 전 태스크 `done`** — “큐에 남은 자동 숙제”는 없음.
- **병목은 ‘실행 자체’보다** (1) **운영/승인 단계와 자동화의 경계**, (2) **heavy vs quick·스킵 정책**, (3) **큐/산출물의 Git 추적 여부**, (4) **다수의 비활성화된 스케줄 작업**에서 오는 **의사결정 부하**에 가깝게 관측됨.

---

## 2. 아키텍처 스냅샷 (확인된 것만)

| 구분 | 내용 |
|------|------|
| 연속 루프 | `apply_trackc_plan_bridge_to_queue_v1.py --merge-existing` 후 `mkm_orchestrator_poll_v1.py` 주기 실행 |
| Quick 폴 | `--skip-heavy` 사용 시 `runtime_class=heavy` 태스크는 기록상 `heavy_task_skipped` |
| Heavy 폴 | `--heavy-only`를 **N 사이클마다** 별도 실행(등록값 예: `HeavyEveryCycles 3`) |
| 별도 폴 작업 | `MKM_OrchestratorPoll` 미등록 시, 분 단위 폴은 데몬 루프에 의존 |
| 감사 로그 | `reports/mkm_orchestrator_audit.jsonl` |
| 큐 파일 | 기본 `docs/final/artifacts/todo_queue_latest.json` — **`.gitignore`로 커밋 제외** |
| 브리지 소스 | `docs/final/artifacts/mkm_trackc_plan_orchestrator_bridge_v1.json` 등 (플랜 마일스톤 변경 시 수동 편집 후 재적용) |

---

## 3. 관측된·유추 가능한 병목지점

### 3.1 의미 대비 자동화 (게이트 설계)

- **클라이언트 핸드오프 가드**는 “운영 홀드(`HOLD_OPERATIONAL_V1`) + 산출 완비”와 “최종 승인(`APPROVED_FINAL_V2`)”을 구분해야 함. 자동 큐가 **실패/통과**를 반복하면 원인은 코드보다 **승인 상태 정의**인 경우가 많음.

### 3.2 Heavy 작업의 주기·비용

- Quick 폴에서 heavy 스킵 → **무거운 빌드/게이트 스모크**는 heavy 주기에만 실행. 주기가 길면 “무중단”은 유지되지만 **피드백 지연**이 생김. 짧으면 **CPU·디스크·다른 스케줄 작업과 경합**.

### 3.3 큐 상태와 Git

- `todo_queue_latest.json`이 저장소에 없으면 **클론·다른 PC·CI**에서 “오케스트레이터가 무엇을 했는지” 재현하기 어렵음. 반대로 로컬 전용 런타임 파일을 커밋하면 **노이즈·충돌** 위험.

### 3.4 스케줄 작업 스프awl

- 동일 머신에 **MKM 접두 작업이 매우 많고**, 다수가 **Disabled**. 어떤 것이 본선·어떤 것이 실험인지 **문서·체크리스트 없이는** 상위 판단이 어려움.

### 3.5 HITL·Telegram·승인 백로그

- 오케스트레이터 설계상 **승인 필요 태스크**는 자동만으로 끝나지 않음. 알림 채널·백로그 파일이 비어 있으면 **조용히 멈춘 것처럼** 보일 수 있음.

---

## 4. 원활한 자율 작업을 위해 (가설로 적어둔 필요 조건)

- **단일 SSOT:** “무엇이 본선 자동화이고, 무엇이 연구/B-track인지” 한 페이지 또는 레지스트리.
- **큐/산출 정책:** 로컬 큐를 커밋할지, 대신 `audit`·요약 JSON만 커밋할지, 실패 시 **누가** `pending`을 되살릴지.
- **Heavy 예산:** 일당 상한·동시 1개·실패 시 exponential backoff 등 **명시적** 정책.
- **승인 경로:** `awaiting_approval` 태스크의 SLA(몇 시간 내 처리)·대체 담당.
- **푸시/동기화:** 로컬 커밋이 쌓인 채 `internal` 미반영이면 **다른 환경과 괴리**.

(위는 레포 규칙·Fact-Lock과 충돌 시 **레포 SSOT가 우선**.)

---

## 5. 상위 모델에게 묻는 질문서 (복사해 사용)

아래는 답변 요청용입니다. 번호 그대로 붙여 질문해도 됩니다.

### A. 아키텍처·경합

1. **Quick 폴에 `--skip-heavy` + 주기적 `--heavy-only`** 패턴에서, dev 머신 1대 기준 **HeavyEveryCycles·LoopSeconds**의 권장 범위와, **피드백 지연 vs 부하** 트레이드오프를 어떻게 잡는 게 좋은가?

2. 동일 호스트에 **수십 개의 Task Scheduler 작업(MKM_*)**이 있을 때, **운영 필수 집합을 최소화**하는 실무 기준(예: 한 주 시나리오 표)은 무엇인가?

3. 오케스트레이터 **파일 락**(`mkm_orchestrator_poll.lock`)과 수동 `poll --skip-lock`이 공존할 때, **데드락·이중 실행**을 피하는 운영 규칙을 어떻게 문서화하는 게 좋은가?

### B. 큐·Git·재현성

4. `todo_queue_latest.json`을 **gitignore**할 때, **재현성·감사**를 위해 최소한 어떤 산출물을 **반드시 커밋**하는 패턴이 좋은가? (예: 주간 큐 스냅샷, 실패 시만 freeze 등.)

5. 브리지 JSON → 큐 병합(`--merge-existing`)이 **장기간** 돌 때 **상태 드리프트**(같은 task_id의 이력 꼬임)를 막는 운영 습관은?

### C. 의미·승인·자동화 경계

6. **운영 홀드**와 **최종 승인**이 공존할 때, 자동 게이트를 **한 개의 exit code**로 통합할지, **tier별 리포트**(예: operational_pass vs final_pass)로 나눌지 — CI·일일 러너·고객 인도 각각에 대한 권장 패턴은?

7. `awaiting_approval` 태스크가 **조용히 쌓이는** 실패 모드를 줄이기 위한 **최소 알림·에스컬레이션** 설계는?

### D. 스케일·다음 단계

8. 지금 구조를 **단일 Windows 로그온 데몬**에서 **서비스/리눅스 runner/CI**로 옮길 때, **가장 먼저 이전해야 할 3가지**와 **나중에 옮겨도 되는 것**은 무엇인가?

9. “무중단”을 **가동 시간**이 아니라 **의미 있는 진철**(예: 주간 게이트 통과 횟수)으로 측정하려면 **어떤 KPI·대시보드 필드**를 최소로 두면 되는가?

10. 이 레포처럼 **규칙·SSOT·Fact-Lock**이 강한 모노레포에서, 자율 에이전트가 **파일을 고치지 않고** 조언만 할 때와 **PR까지** 할 때의 **책임 분리**를 어떻게 두는 것이 안전한가?

---

## 6. 제약·면책 (상위 모델 답변 시)

- 실거래·규제·고객 계약은 **본 문서와 무관**하며, 자동화 **ON/OFF**는 별도 인간 승인 게이트가 우선이다.
- 외부 URL·키·VPS 상태는 **미검증**이면 답변에 “가정”을 명시할 것.

---

**파일 위치:** `reports/mkm_autonomy_status_and_questions_for_upper_model_v1.md`  
상위 모델에 넘길 때는 **섹션 1~3(현황·병목)** 과 **섹션 5(질문)** 만 붙여도 충분하고, 전략 답변·백로그는 `docs/governance/mkm_operational_standard_v1.md` 와 함께 보내면 된다. 레포 내부 세부는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 등으로 위임 가능.
