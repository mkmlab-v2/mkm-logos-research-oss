# 일반 예언(제1전선) · 월간 체인 — Windows 작업 스케줄러 런북 v1

**역할:** `scripts/run_waiting_queue_monthly_check.ps1` 안의 **일반 예언(B 레일)** 체인(`generate_general_prophecy_v1.py` → `build_general_prophecy_brief.py` → `eval_general_prophecy_brier_score.py`)이 **월간으로 돌도록** 호스트에서 스케줄만 잡을 때의 SSOT다. A-track 실거래·제2전선(KOSPI/BTC 일일)과 **절차 혼동 금지**.

## 사전 조건

- 작업 디렉터리: 모노레포 루트(예: `C:\workspace`). 환경 변수 `MKM_WORKSPACE_ROOT`가 있으면 일부 스크립트가 이를 우선한다.
- Python: `py` 가 PATH에 있음(프로젝트 규칙).
- `generate_general_prophecy_v1.py`는 기본 머지로 **시드5 + Brier 스모크 + 거시 H2 2026 팩**을 합쳐 **12문항** 레지스트리를 만든다(`--no-default-merge` / `-SkipGeneralProphecyChain`로 끌 수 있음).

## 권장: 월간 원샷(전체 체인)

전체 월간 감사·브리프·(설정 시) Slack까지 포함하려면 **이것만 스케줄**한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_waiting_queue_monthly_check.ps1"
```

일반 예언만 끄려면 스크립트에 `-SkipGeneralProphecyChain`를 붙인다(의도·감사 로그에 이유를 남길 것).

## 일반 예언 3단계만 수동 스모크할 때

```powershell
Set-Location C:\workspace
py scripts/generate_general_prophecy_v1.py
py scripts/build_general_prophecy_brief.py
py scripts/eval_general_prophecy_brier_score.py
```

산출(기본): `docs/final/artifacts/general_prophecy_latest.json`, `general_prophecy_brief_latest.md`, `general_prophecy_brier_eval_latest.json`.

## 작업 스케줄러 등록 예시

- **작업 이름(예):** `MKM-WaitingQueue-MonthlyCheck`
- **트리거:** 매월 1일 07:00(로컬) 등 — 지휘관 PC 기준으로만 고정.
- **동작:** 위 `run_waiting_queue_monthly_check.ps1` 한 줄.
- **조건:** 실패 시 재시작 N회는 팀 정책; AC 전원 해제 시 “사용자 로그온 시만” 등 옵션은 호스트마다 다름.

상용화·증거 표: `docs/final/P0_COMMERCIALIZATION_TRACKER.md` 월간 절.
