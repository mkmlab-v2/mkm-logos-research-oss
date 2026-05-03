# MKM 운영 표준 v1 (Operational Standard)

**schema:** `mkm_operational_standard_v1`  
**version:** 1.0.0  
**status:** ADOPTED_AS_SSOT_DRAFT  
**effective_note:** 본 문서는 **전략 지휘 계통(Strategic Guidance)** 과 레포 현황 보고를 통합한 **운영 규약 초안**이다. 코드·스크립트의 즉시 변경을 단정하지 않으며, **구현 여부는 항상 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 실행 파일·exit code로 검증**한다 (Fact-Lock).

**관련 보고:** `reports/mkm_autonomy_status_and_questions_for_upper_model_v1.md`

---

## 1. 목적과 범위

**목적:** MKM 무중단 자율 루프를 **지속 가능한 운영(Sustainable Ops)** 및 **규제·거버넌스 준수(Governed)** 단계로 올리기 위한 공통 언어와 우선순위를 고정한다.

**범위:** 로컬·스케줄러·오케스트레이터(`todo_queue_v1`, MKM 연속 데몬, 감사 로그).  
**범위 밖:** 실거래 ON/OFF, 외부 규제 최종 판단, 고객 계약 — 별도 **인간 승인 게이트**가 상위다.

---

## 2. 운영 철학 (한 줄)

**Autonomous yet Governed:** 자동화는 넓히되, **승인 계층·감사 가능성·재현 가능한 증거**로 통제 가능해야 한다.

---

## 3. 전략 가이드라인 (상위 지휘 관점 요약)

아래는 질문 Q1–Q10에 대한 **전략적 답변**을 레포 규약 형태로 재구성한 것이다.

### A. 아키텍처 및 부하 관리

**Quick vs Heavy (Q1)**

- **의도:** Quick 폴은 짧은 **상태 확인**에 집중하고, Heavy는 **검증·빌드·큰 비용**에 할당한다.
- **권장 탐색 범위 (가이드):** `LoopSeconds` 약 60초 유지 시, **`HeavyEveryCycles` 10–20** (대략 **10–20분**마다 Heavy 전용 폴)을 우선 검토한다. 현재 로컬 등록값이 그보다 짧다면 **부하·피드백 지연**을 함께 보고 조정한다.
- **원칙:** 피드백 지연만큼이 아니라 **환경·컨텍스트 드리프트(Drift)** 방지가 운영 안정성에 더 치명적일 수 있다 — Heavy 주기는 인간 주의 주기(예: 15–20분 점검 리듬)와 맞추는 것을 허용한다.

**작업 스케줄 단순화 (Q2)**

- **방향:** 다수의 Windows 작업(MKM_*…)을 **단일 진입점**으로 수렴시키는 패턴을 장기 목표로 둔다.
- **패턴 (목표 아키텍처):** 단일 **`MKM_Master_Orchestrator`**(가칭)가 내부 **`tasks_config.json` 매니페스트**를 읽어 분기하고, **Task Scheduler는 마스터 데몬 생존·헬스만** 감시한다.
- **Fact-Lock:** 현재 레포에 해당 바이너리·매니페스트가 없으면 **미구현**로 두고, 신규 작업 등록 시 본 표준을 참조한다.

**파일 락 (Q3)**

- **`--skip-lock`:** **긴급 복구·단발 수동 실행**에 한정한다.
- **평시:** 오케스트레이터에 **대기·재시도(Wait-and-Retry)** 를 두어 **이중 실행**을 원천적으로 줄인다 (구현 시 `scripts/mkm_orchestrator_poll_v1.py` 락 경로와 함께 검토).

### B. 데이터 무결성 및 재현성

**Git 전략 (Q4)**

- **`todo_queue_latest.json`:** 로컬 런타임 특성상 **`.gitignore` 유지** 가능.
- **대신:** 일·주 단위 **정산 아티팩트**를 자동 생성해 커밋하는 패턴을 권장한다. 예: `docs/audit/weekly_summary_{date}.json` (경로는 레포 관례에 맞게 확정). **큐 전체가 아니라 결과·증거** 위주로 버전 관리하여 노이즈를 줄인다.

**상태 드리프트 (Q5)**

- **task_id 불변성:** 필요 시 **타임스탬프·해시** 결합 등으로 충돌을 줄인다.
- **병합:** 동일 ID 충돌 시 무작정 덮어쓰지 않고 **`conflict_v1` 분리·append-only** 습관을 권장한다 (`apply_trackc_plan_bridge_to_queue_v1.py` 등 병합 로직 변경 시 본 표준 준수).

### C. 거버넌스 및 승인

**승인 계층 (Q6)**

- **Operational Pass:** 기술적 무결성 — CI/게이트·환경 GREEN, 산출 스키마 일치 등.
- **Final Pass:** 비즈니스 정당성 — 예산·리스크·대외 약속 등 **인간(HITL)** 영역.
- **상용 기본:** Operational까지는 자동화 허용 범위를 넓히고, Final은 **명시적 승인** 후로 분리하는 것을 표준 방향으로 둔다.  
  (Track C 핸드오프 가드의 **`--strict-final`** 등은 Final 층의 기술적 게이트 예시로 유지.)

**에스컬레이션 (Q7)**

- **`awaiting_approval` 장기 체류:** 예시 정책 — **4시간 초과** 시 `stale` 표시, 알림(예: 텔레그램) **1회 재발송**, **의존 태스크 일시 `paused`**.  
- **Fact-Lock:** 텔레그램·템플릿은 `CONSTITUTION`·기존 스크립트 경로가 우선; 미구현이면 본 절은 **요구사항**으로만 둔다.

### D. 확장 및 미래 가치

**이전 우선순위 (Q8)**

1. **감사 로그·상태의 중앙화** (단일 조회면으로 수렴).
2. **비밀값 주입 브로커** (호스트별 `.env`, 브로커 패턴).
3. **태스크 러너(CI/CD Runner)** — UI·쉘 의존 작업은 **후순위** 이전.

**진척 KPI (Q9)**

- **Gate-Pass Efficiency:** 주간 목표 대비 게이트 통과 비율.
- **Mean Time to Approval:** 승인 대기 시간 평균·분포.
- **Drift Frequency:** 환경 불일치·스키마 드리프트 발생 빈도.

**책임 분리 (Q10)**

- 에이전트 **조언**과 **코드 변경(PR)** 을 분리한다.
- PR·머지는 **인간 지휘관·정책 게이트**가 최종 권한을 가진다 — Fact-Lock 및 Athena Doctor 류 검증과 정렬할 때 본 절을 상위 원칙으로 둔다.  
  (**구현 상태는 레포 스크립트·문서로만 단정.**)

---

## 4. 다음 구현 백로그 (오케스트레이터·운영 패치)

우선순위는 지휘관이 조정한다. 아래는 본 표준과의 **명시적 연결**이다.

| 우선 | 항목 | 참조 코드·산출 |
|------|------|----------------|
| P0 | 락 대기·재시도 (평시 이중 실행 방지) | `scripts/mkm_orchestrator_poll_v1.py`, `reports/mkm_orchestrator_poll.lock` |
| P1 | Heavy 주기 조정 가이드 반영 (10–20분 탐색) | `scripts/run_mkm_continuous_daemon.ps1`, 등록된 Scheduled Task 인자 |
| P1 | 주간 정산 아티팩트 생성·커밋 후보 | 신규 스크립트 또는 기존 audit 요약 체인 |
| P2 | `awaiting_approval` stale·에스컬레이션 | `mkm_orchestrator_poll_v1.py`, `approve_mkm_orchestrator_task_v1.py`, 텔레그램 연동 |
| P3 | 마스터 오케스트레이터 + 매니페스트 | 신규 설계·단계적 이전 |

---

## 5. 개정

- 개정 시 **버전 번호·변경 요약**을 본 파일 상단에 남긴다.
- 헌법 수준 문구와 충돌 시 **루트 `.cursorrules` · `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`** 가 우선한다.

---

**선포 문구 (운영 메모):** 본 v1은 **“구동 단계”에서 “지속 가능·통제 가능 운영 단계”로의 이정표**를 문서화한 것이며, 실제 시스템 동작은 항상 **디스크 산출·exit code·감사 로그**로 검증한다.
