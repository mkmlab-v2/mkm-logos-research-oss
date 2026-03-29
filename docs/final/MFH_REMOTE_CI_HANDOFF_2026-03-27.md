# MFH Remote CI Handoff (2026-03-27)

## 문서 메타

- 날짜: 2026-03-27
- 범위: Med/Fin/Han 보조 전선 — 원격 저장소에서 **Guardian Contract Gate** / **Master Codebook Training Smoke Gate** 증거 수집·판정
- 관련 SSOT:
  - `docs/final/DSS_APOCRYPHA_FRONTLINE_CLOSEOUT_2026-03-27.md`
  - `docs/final/MFH_REMOTE_CI_CYCLE6_RESULTS_2026-03-27.md`
  - `docs/final/NO1KMEDI_RECOVERY_TASKLIST_2026-03-27.md`

---

## Executive (3줄)

- 원격 대상 저장소: `mkmlab-v2/mkm-destiny-ai-41e38ec6`; 보조 전선은 DSS `ext3` 주력과 **파일 경로 분리**를 유지한다.
- 증거 수집은 `gh workflow run`으로 dispatch 후 `gh run list`로 최신 run을 고정하고, **결론·URL·run_id**를 Cycle6 결과 문서에 기록한다.
- 2026-03-27 Cycle 6 판정은 **HOLD**(양 workflow 모두 failure); 상세 run URL·실패 원인은 `MFH_REMOTE_CI_CYCLE6_RESULTS_2026-03-27.md`가 단일 증거 슬롯이다.

---

## [FACT] Workflow 이름 (dispatch용)

| 역할 | Workflow 표시명 |
|------|------------------|
| Guardian | `no1kmedi Guardian Contract Gate` |
| Smoke | `Master Codebook Training Smoke Gate` |
| (참고·DSS 주력) | `Frontline Release Check` |

---

## 재현·디스패치 명령 (PowerShell)

```powershell
gh workflow run "no1kmedi Guardian Contract Gate" -R mkmlab-v2/mkm-destiny-ai-41e38ec6
gh workflow run "Master Codebook Training Smoke Gate" -R mkmlab-v2/mkm-destiny-ai-41e38ec6

gh run list -R mkmlab-v2/mkm-destiny-ai-41e38ec6 --workflow "no1kmedi Guardian Contract Gate" --limit 1
gh run list -R mkmlab-v2/mkm-destiny-ai-41e38ec6 --workflow "Master Codebook Training Smoke Gate" --limit 1
```

**전제**: 로컬에 `gh` 인증 및 해당 repo에 대한 실행 권한이 있음. remote 미설정 워크스페이스에서는 Cycle 4에서와 같이 **메인 연결 환경**에서 dispatch할 것(`NO1KMEDI_RECOVERY_TASKLIST` 병렬 로그 참고).

---

## PASS / HOLD 보고 규칙

| 판정 | 조건 |
|------|------|
| **GO** | guardian·smoke **모두** `conclusion: success`(또는 동등한 성공 상태) |
| **HOLD** | 한쪽이라도 failure / cancelled / 스크립트 미존재 등으로 실패 |

실패 시 **최소 기록**: `workflow` 이름, `run_id`, `url`, `conclusion`, 로그에서 **1~3줄** 핵심 에러(경로·exit code).

---

## 2026-03-27 증거 고정 (Cycle 6)

- **권위 결과 파일**: `docs/final/MFH_REMOTE_CI_CYCLE6_RESULTS_2026-03-27.md`
- 요약: guardian `23647646169`, smoke `23647647632`, 결론 **failure** 공통 — 원격 default branch에 `scripts/validate_no1kmedi_guardian_contracts.py`, `scripts/run_master_codebook_training_smoke.py` 미동기화로 해석.

---

## Closeout와의 정합

- `DSS_APOCRYPHA_FRONTLINE_CLOSEOUT`에는 guardian/smoke가 **UI·브랜치 노출 관점**에서 “미확인/URL 회수 불가”로 적힌 잔여 리스크가 있다.
- **Dispatch가 성공한 실행**에 대한 run-level URL은 Cycle6에 **존재**하므로, “워크플로 미등록”과 “실행 run 부재”는 동일하지 않다. **실패 증거 URL**은 Cycle6를 따른다.

---

## 다음 수정(재시도) 시 체크

1. 메인 저장소 default branch에 위 `scripts/*.py` 두 파일 동기화.
2. 동일 dispatch 명령 재실행 후 `MFH_REMOTE_CI_CYCLE6_RESULTS` 형식으로 새 슬롯에 기록하거나, 동일 파일에 날짜 섹션 추가(팀 규칙에 따름).

---

## Next Action (지휘관 선택)

- **[A]** 원격 `scripts/` 동기화 후 guardian/smoke 재-dispatch → 결과를 Cycle6와 동일 포맷으로 갱신.
- **[B]** DSS Closeout의 Med/Fin 절을 “Cycle6 run URL 존재”에 맞게 한 줄 보정(문서만, 판정 유지).
