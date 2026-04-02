# A-Track Weekly Scheduler Runbook (Slack) v1

목표: 매주 A-Track 상태를 `a_track_go_nogo_status_latest.json`으로 자동 생성하고, Slack Webhook으로 `[A-Track Status: HOLD | S1_SHADOW]` 형태의 알림을 전송한다.  
정책: 기본은 fail-safe이며(시스템 에러면 `NO_GO`), 전송 실패는 로컬 로그로만 남긴다.

---

## 1) 사용 스크립트

- 상태 JSON 생성: `scripts/build_a_track_go_nogo_status.py`
- Slack 전송: `scripts/send_a_track_go_nogo_slack.py`
- 주간 러너(순서 고정): `scripts/run_a_track_weekly_check.ps1`

주간 러너 기본 실행 커맨드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_a_track_weekly_check.ps1" -OnSystemError no_go
```

테스트(실전 전송 스킵) 실행 커맨드:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_a_track_weekly_check.ps1" -OnSystemError no_go -DryRun
```

---

## 2) Slack Webhook 설정 (비밀값)

아래 환경변수 중 하나를 설정한다. (실제 URL은 문서/커밋에 포함하지 않는다.)

- `A_TRACK_SLACK_WEBHOOK_URL` (우선)
- 없으면 `FACT_SAFE_SLACK_WEBHOOK_URL`
- 없으면 `SLACK_WEBHOOK_URL`

`C:\workspace\.env` 파일이 이미 존재한다면, 러너 실행 시 Python이 `.env`를 로드한다.  
따라서 Webhook URL은 로컬 전용 `.env`에 넣는 방식을 권장한다. (`.env`는 Git 커밋 금지)

---

## 3) Windows Task Scheduler 등록 가이드

1. `Task Scheduler` 열기
2. `Create Task...` 선택
3. `General` 탭
   - Name: `A-Track Weekly GoNoGo`
   - Security options: 사용자 컨텍스트는 운영 방식에 맞춰 선택
4. `Triggers` 탭
   - `Weekly` 선택
   - 요일/시간 지정 (운영 환경의 트래픽이 낮은 시간 권장)
5. `Actions` 탭
   - `New...` -> `Start a program`
   - Program/script: `powershell.exe`
   - Add arguments:
     - `-NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_a_track_weekly_check.ps1" -OnSystemError no_go`
   - Start in (선택): `C:\workspace`
6. `Conditions` 탭(권장)
   - 필요 시 “전원/네트워크 절전” 관련 옵션은 해제(스케줄 실패 방지)
7. `Settings` 탭(권장)
   - “If the task fails, restart every ...”는 운영 정책에 맞게 선택

---

## 8) 자동 등록(선호)

아래 스크립트로 Task Scheduler에 작업을 자동 등록할 수 있다.

등록 스크립트:

- `scripts/register_a_track_weekly_gonogo_task.ps1`

기본 등록(월요일 09:30, 실전 전송):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\register_a_track_weekly_gonogo_task.ps1"
```

원하는 요일/시간 지정:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\register_a_track_weekly_gonogo_task.ps1" -WeeklyOn MON -At "09:10"
```

작업 제거:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\register_a_track_weekly_gonogo_task.ps1" -Remove
```

## 4) Slack 메시지 페이로드/포맷

메시지는 Incoming Webhook에 다음 규칙으로 구성된다.

- 상단 타이틀: `A-Track Status: {OVERALL} | {RECOMMENDED_STAGE}`
- 색상(attachments color):
  - `GO` : `#36a64f` (green)
  - `HOLD` : `#ffae42` (orange)
  - 그 외: `#d00000` (red)
- fields:
  - `overall_go_no_go` (short)
  - `recommended_stage` (short)
  - `generated_at_utc` (long)
- 본문에 포함:
  - `high_reliability_decision`
  - `price_output_locked`
  - `chronos_holdout_direction_match_rate`
  - `failed_reasons` (상위 30개까지)

---

## 5) 로그/추적성

전송 여부 및 실패 추적은 아래 JSONL에서 확인한다.

- `docs/final/artifacts/a_track_go_nogo_slack_delivery_log.jsonl`

각 행에는 `dry_run` / `webhook_sent` / `payload_summary`가 기록된다.

---

## 6) 장애 시 동작(Fail-Safe)

- 상태 JSON 입력 누락/손상 등 “시스템 에러”면 기본 정책은 `NO_GO`로 강제한다.
- 단, operator continuity가 필요할 때만 예외적으로 `-OnSystemError hold_s1` 옵션을 쓴다.

---

## 7) 운영 체크(최초 1회)

최초 등록 후, `-DryRun`으로 1회 테스트 -> 실제 Webhook 전송 1회 테스트 순으로 검증한다.
검증 목표:
1) `a_track_go_nogo_status_latest.json` 생성 성공
2) Slack 도착 여부 및 `HOLD | S1_SHADOW`가 기대와 일치
3) `failed_reasons`가 사유 기반으로 읽히는지 확인

