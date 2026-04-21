# SSH Cursor Bitcoin Trading Clear Runbook v2 (Single Mode, 2026-04-22)

## 목적
- SSH Cursor 작업 시 저장소 불일치로 인한 혼선을 제거한다.
- 비트코인 운영을 단일 전략으로 고정하고, 검증 체인은 비거래 모드로만 수행한다.

## 절대 원칙
- 서버 운영 원격을 임의 변경하지 않는다.
- 검증 스크립트가 없는 상태에서 승격(Go) 판단을 하지 않는다.
- `A-track HOLD/S1_SHADOW` 상태에서는 메인 전략만 유지하고, 병렬 매매를 금지한다.

## Phase 0: 서버 상태 고정 확인 (필수)
```bash
cd /opt/mkm-lab-workspace-v2/projects/bitcoin-trading
git remote -v
git branch -vv
git rev-parse --short HEAD
```

판정:
- 원격이 `git@github.com:mkmlab-hq/mkm-lab-workspace-v2.git`이면 이 런북 그대로 진행.
- 다른 원격이면 즉시 중지 후 운영 책임자에게 보고.

## Phase 1: 단일 매매 모드 강제 (즉시 적용)
```bash
pm2 status
pm2 stop bitcoin-live-treatment || true
pm2 delete bitcoin-live-treatment || true
pm2 restart bitcoin-live
pm2 save
```

운영 규칙:
- `bitcoin-live` = 기존 메인 전략 유지
- `bitcoin-live-treatment` = 사용 금지(중지/삭제 상태 유지)
- 검증 결과와 무관하게 메인 전략 대체 금지

## Phase 2: 최소 이식 PR 수행 지시 (SSH Cursor 작업)
아래 파일이 서버 리포에 없으면 반드시 이식 PR을 먼저 수행한다.

필수 이식 대상(14):
- `scripts/run_gematria_4d_gate.py`
- `scripts/spike_gematria_myeongri_blend_v0.py`
- `scripts/run_btrack_fusion_gate.py`
- `scripts/build_btrack_promotion_signoff_packet_v1.py`
- `scripts/fast_promotion_gate_v1.py`
- `scripts/build_a_track_go_nogo_status.py`
- `scripts/join_symbol_vector_4d.py`
- `scripts/report_symbol_gematria_alignment.py`
- `scripts/report_gematria_4d_uplift_ab.py`
- `scripts/check_gematria_4d_gate.py`
- `scripts/run_deut32_cee_pilot.py`
- `scripts/run_deut32_cee_stability_sweep.py`
- `scripts/core/build_original_language_master_atoms.py`
- `scripts/check_master_atoms_health.py`

브랜치 생성:
```bash
git checkout -B feature/port-btrack-gematria-fusion-gates
```

## Phase 3: 이식 완료 후 검증 체인 실행 순서 (고정)
아래 순서 외 실행 금지:
```bash
python3 scripts/run_gematria_4d_gate.py
python3 scripts/spike_gematria_myeongri_blend_v0.py
python3 scripts/run_btrack_fusion_gate.py
python3 scripts/build_btrack_promotion_signoff_packet_v1.py
python3 scripts/fast_promotion_gate_v1.py
python3 scripts/build_a_track_go_nogo_status.py
```

## Phase 4: 최종 판정 키 (3개 JSON만 본다)
- `reports/constitution/btrack_pilot/btrack_fusion_gate_latest.json`
  - `decision`
- `docs/final/artifacts/fast_promotion_gate_v1_latest.json`
  - `result.live_ready`
- `docs/final/artifacts/a_track_go_nogo_status_latest.json`
  - `result.overall_go_no_go`
  - `result.recommended_stage`

판정 규칙:
- `decision=pass` AND `result.live_ready=true`여도
- `overall_go_no_go=HOLD`이면 운영은 제한 모드 유지 (`S1_SHADOW`)

## Phase 5: 단일 매매 운영 체크
```bash
pm2 status
pm2 logs bitcoin-live --lines 120
```

확인 항목:
- `bitcoin-live`만 online
- `bitcoin-live-treatment` 프로세스가 목록에 없음
- 검증 체인 실행 중에도 주문/포지션 로직 변경 없음

## 장애 시 즉시 롤백
```bash
pm2 restart bitcoin-live
pm2 logs bitcoin-live --lines 200
```

추가 원칙:
- 메인 프로세스(`bitcoin-live`)는 중지하지 않는다(장애 전파 방지).
- 원인 파악 전 재시도 반복 금지.

## Phase 6: 일일 검증 + 주 1회 반자동 진화 (비거래)
목표:
- 매일 예언 생성/정답 비교 루프를 유지한다.
- 주 1회만 파라미터 탐색/후보 비교를 수행하고, 반영은 수동 승인으로 제한한다.

일일(매일 1회, 비거래):
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_daily_prophecy_eval_and_report.ps1" -IncludeDatedArchive
```

주간(주 1회, 비거래/후보 생성):
```bash
py "scripts/run_prophecy_per_date_combo_walkforward_v1.py"
py "scripts/run_prophecy_instrument_combo_walkforward_v1.py"
py "scripts/refresh_prophecy_promotion_gates_dual_v1.py"
py "scripts/fast_promotion_gate_v1.py"
py "scripts/build_a_track_go_nogo_status.py"
```

주간 판정 규칙:
- `fast_promotion_gate_v1_latest.json`의 `result.live_ready=true`여도
- `a_track_go_nogo_status_latest.json`이 `HOLD/S1_SHADOW`면 운영 정책 변경 금지
- 주간 실행 결과는 "후보 리프레시"로만 기록하고, 실매매 전략 자동 교체 금지

수동 승인 없이는 금지:
- 메인 전략 파라미터 변경
- 주문 라우팅 규칙 변경
- A-track 승격 선언

## SSH Cursor 전달용 단문 지시
아래 문장을 그대로 전달:

"서버 원격(`mkmlab-hq/mkm-lab-workspace-v2`) 기준으로만 작업. 단일 매매 정책이므로 `bitcoin-live-treatment`은 stop/delete 유지, `bitcoin-live`만 운영. 14개 B-track 검증 스크립트 이식 PR 후 python3 1~6 고정 체인 실행, 마지막에 3개 JSON 키(decision/live_ready/overall_go_no_go+recommended_stage)만 보고. HOLD면 S1_SHADOW 제한 운영 유지, 메인 전략 단일 유지."

## Deployment Record
- 2026-04-22: `mkmlab.space` landing updated to self-hosted promo video (`/media/promo.mp4`) and cache-busted assets (`main.css`/`main.js` at `?v=20260422-2`), deployed via `mkmlab-redesign_20260422_032053.zip`.
- 2026-04-22: PR #25 merge 이후 `hq/main` 동기화 완료, `mkmlab-redesign` 핵심 파일 5종 존재 확인, runbook `Worktree 고정 운영 표준` 섹션 확인, `https://mkmlab.space/media/promo.mp4` 및 `main.css/main.js?v=20260422-2` HTTP 200 응답 확인.

## Worktree 고정 운영 표준 (클린 배포/동기화)
목표:
- 더티 워킹트리와 운영 작업을 물리적으로 분리한다.
- 배포/동기화/핫픽스는 상시 클린 worktree에서만 수행한다.

기본 경로(로컬 표준):
- 메인 작업 트리: `C:\workspace` (더티 상태 허용)
- 클린 운영 트리: `C:\workspace\_ops_clean_hq`

최초 1회 설정:
```bash
cd C:\workspace
git remote get-url hq || git remote add hq git@github.com:mkmlab-hq/mkm-lab-workspace-v2.git
git fetch hq
git worktree add C:\workspace\_ops_clean_hq hq/main
```

일상 운영(배포/동기화/핫픽스 전용):
```bash
cd C:\workspace\_ops_clean_hq
git fetch hq
git checkout main
git pull --ff-only hq main
git status
```

작업 규칙:
- `C:\workspace`에서 배포용 checkout/cherry-pick/merge 금지
- 운영 반영은 `C:\workspace\_ops_clean_hq`에서만 수행
- 필요한 경우 임시 worktree를 추가 생성해 브랜치별 격리 수행

작업 종료/정리:
```bash
cd C:\workspace
git worktree list
git worktree remove C:\workspace\_ops_clean_hq
git worktree prune
```
