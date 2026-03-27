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

## 결과 기록

- guardian gate:
  - run_id: `23647646169`
  - conclusion: `failure`
  - url: `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23647646169`
- smoke gate:
  - run_id: `23647647632`
  - conclusion: `failure`
  - url: `https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/actions/runs/23647647632`

---

## 판정

- decision: `HOLD`
- 근거:
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
