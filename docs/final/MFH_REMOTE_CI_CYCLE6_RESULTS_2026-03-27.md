# MFH Remote CI Cycle 6 Results (2026-03-27)

## 문서 메타

- 날짜: 2026-03-27
- 목적: Med/Fin/Han 보조 전선의 원격 CI 실행 결과를 증거 기반으로 수집/판정
- 기준 문서:
  - `docs/final/MFH_REMOTE_CI_HANDOFF_2026-03-27.md`
  - `docs/final/NO1KMEDI_RECOVERY_TASKLIST_2026-03-27.md`

---

## 실행 커맨드

```powershell
gh workflow run "no1kmedi Guardian Contract Gate" -R mkmlab-v2/mkm-destiny-ai-41e38ec6
gh workflow run "Master Codebook Training Smoke Gate" -R mkmlab-v2/mkm-destiny-ai-41e38ec6

gh run list -R mkmlab-v2/mkm-destiny-ai-41e38ec6 --workflow "no1kmedi Guardian Contract Gate" --limit 1
gh run list -R mkmlab-v2/mkm-destiny-ai-41e38ec6 --workflow "Master Codebook Training Smoke Gate" --limit 1
```

---

## 결과 기록 (2026-03-27 초기 실행 — 역사 기록, superseded)

- guardian gate:
  - run_id: `23647646169`
  - conclusion: `failure`
  - url: `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23647646169`
- smoke gate:
  - run_id: `23647647632`
  - conclusion: `failure`
  - url: `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23647647632`

---

## 2026-03-29 복구 · 전체 CI 스위트 (Fact-Lock)

`main` ↔ `origin` 동기화 후 동일 저장소에서 `workflow_dispatch`/push 연쇄로 확인한 **최신 성공** 실행( `gh run list` 기준, branch `main` ).

| Workflow | run_id | conclusion | url |
| :--- | :--- | :--- | :--- |
| no1kmedi Guardian Contract Gate | `23699819562` | success | `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23699819562` |
| Master Codebook Training Smoke Gate | `23699819948` | success | `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23699819948` |
| Dual Regime Integrity (Fact-Lock) | `23699895072` | success | `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23699895072` |
| Frontline Release Check | `23699895436` | success | `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23699895436` |

- 판정: **`PASS` / Fact-Locked** — 위 네 워크플로가 2026-03-29 UTC 기준 원격에서 **모두 success**로 종료됨.

---

## 판정 (2026-03-27 시점 — superseded)

- decision: `HOLD` → **2026-03-29에 `PASS`로 대체** (아래 복구 섹션 참조)
- 근거 (당시):
  - guardian: 스크립트 경로 누락으로 실행 실패
  - smoke: 스크립트 경로 누락으로 실행 실패

---

## 실패 시 요약

- failing workflow: `no1kmedi Guardian Contract Gate`
- failing job: `guardian-contract-gate`
- 핵심 에러 1~3줄:
  - `python: can't open file ... scripts/validate_no1kmedi_guardian_contracts.py`
  - `Process completed with exit code 2`
- 재시도/수정 계획:
  - 메인 저장소 default branch에 `scripts/validate_no1kmedi_guardian_contracts.py` 파일 동기화 후 재실행

- failing workflow: `Master Codebook Training Smoke Gate`
- failing job: `training-smoke-gate`
- 핵심 에러 1~3줄:
  - `python: can't open file ... scripts/run_master_codebook_training_smoke.py`
  - `Process completed with exit code 2`
- 재시도/수정 계획:
  - 메인 저장소 default branch에 `scripts/run_master_codebook_training_smoke.py` 파일 동기화 후 재실행
