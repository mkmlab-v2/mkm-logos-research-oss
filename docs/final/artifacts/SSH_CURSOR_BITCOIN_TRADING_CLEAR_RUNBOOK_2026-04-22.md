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

## 선택: 로컬 Financial Sovereign 백테스트 스모크 (비거래, PR/CI 전)
데이터 소스 우선순위: (1) `research/market_data/btc_daily_external_yf.csv`(로컬·미추적 가능) (2) 레포 추적 픽스처 `projects/bitcoin-trading/tests/fixtures/btc_smoke_daily.csv`(CI 기본). 둘 다 없으면 **SKIP exit 0**(stderr 안내). 반드시 데이터가 있어야 할 때만 `MKM_SOVEREIGN_SMOKE_REQUIRE_DATA=1`. 주문·PM2와 무관.

```powershell
cd C:\workspace\projects\bitcoin-trading
python scripts\smoke_financial_sovereign_backtest.py
echo $LASTEXITCODE   # 0 이면 통과 또는 SKIP
```

Linux(모노레포 예: `/opt/mkm-lab-workspace-v2`):

```bash
cd /opt/mkm-lab-workspace-v2/projects/bitcoin-trading && python3 scripts/smoke_financial_sovereign_backtest.py
```

동일 기능을 인자로 직접 쓸 때는 `scripts/run_financial_sovereign_backtest_cli.py --help` 참고. 결과는 `projects/bitcoin-trading/data/` 아래 JSON에 기록된다(`schema`: `financial_sovereign_backtest_cli_v2`, 스모크 출력은 보통 `_smoke_financial_sovereign_backtest.json`).

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

## Phase 7: Factor Influence 30분 자동 집계 (SSH 운영)
목표:
- `pm2` 실로그 기준으로 최근 1200라인/24h 근사치를 함께 산출한다.
- `factor_influence_latest.json`를 30분마다 갱신하고, **원인 버킷(breakdown)**·**알림 상태**를 함께 기록한다.

로그 선택:
- **진단 태그(`vector_missing`, `engine_fallback_ma` 등)** 는 운영 기준 **`bitcoin-live-error.log`** 에 많이 실린다. 스크립트 기본값·크론 등록 스크립트 기본도 이 경로로 맞춘다.
- 표준 출력만 보려면 `--log-file /root/.pm2/logs/bitcoin-live-out.log` 로 바꿔 실행한다.

본선 크론(권장 엔트리):
```bash
/usr/bin/python3 /opt/mkm-lab-workspace-v2/projects/bitcoin-trading/scripts/report_factor_influence_latest.py \
  >> /opt/mkm-lab-workspace-v2/projects/bitcoin-trading/logs/factor_influence_cron.log 2>&1
```
(동일 로직을 레포 스크립트로 등록하려면 아래 `register_*` 참고.)

수동 1회 실행:
```bash
cd /opt/mkm-lab-workspace-v2/projects/bitcoin-trading
python3 scripts/report_factor_influence_latest.py \
  --log-file /root/.pm2/logs/bitcoin-live-error.log \
  --out-dir exports/cursor_trade_history \
  --recent-lines 1200 \
  --window-hours 24 \
  --emit-legacy-files
```

임계치(환경변수, 선택): `FACTOR_INFLUENCE_CRIT_VECTOR`, `FACTOR_INFLUENCE_CRIT_ENGINE`(기본 0.5), `FACTOR_INFLUENCE_ESCALATE_AFTER`(기본 2회 연속 CRITICAL 쌍이면 `critical_action_required`).

슬림 전용(알림·breakdown 없이 구 스키마 `factor_influence_latest_v1`만 필요할 때):
```bash
python3 scripts/build_factor_influence_latest.py \
  --log-file /root/.pm2/logs/bitcoin-live-error.log \
  --out-dir exports/cursor_trade_history \
  --recent-lines 1200 \
  --window-hours 24 \
  --emit-legacy-files
```

30분 크론 등록:
```bash
cd /opt/mkm-lab-workspace-v2/projects/bitcoin-trading
bash ops/v2/ssh/register_factor_influence_latest_cron.sh
crontab -l | grep bitcoin-factor-influence-latest
```
크론에서 표준 출력 로그를 쓰려면 등록 전에 한 줄만 지정한다:  
`export LOG_FILE=/root/.pm2/logs/bitcoin-live-out.log`

### hq 저장소 반영 (한 줄)
로컬에만 있는 체리픽 커밋을 **`mkmlab-hq/mkm-lab-workspace-v2`** 의 `main`에 올리려면 클린 워크트리에서 예를 들면:
```bash
git fetch hq && git cherry-pick 9727be0e   # 또는 VPS에 반영한 동일 변경의 커밋 해시
git push hq main
```
(VPS와 동일 내용이면 해시만 맞추면 된다.)

핵심 확인 파일:
- `exports/cursor_trade_history/factor_influence_latest.json` — 상단 `exported_at`, `trade_done_rate` / `vector_missing_rate` / `engine_fallback_ma_rate`, `recent_lines.breakdown`
- `exports/cursor_trade_history/factor_influence_alert_state.json` — `severity`, `consecutive_critical_count`, `repeat_alert_suppressed`
- `exports/cursor_trade_history/factor_influence_recent_lines.json` / `factor_influence_24h.json` — `--emit-legacy-files` 시

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

## Pre-News 아침 체인 (로컬 관측, 실매매 자동 합선 없음)
- 운영 정책(2026-04-22): **평시 SSH Cursor 미사용**, 로컬 단일 체인 우선. 원격은 비상 시 `-EmergencyOverride`로만 사용.
- 스냅샷: `py scripts\build_pre_news_snapshot_v1.py` (선택 `--yf-fetch`)
- dual_regime 벤치 브리지: `py scripts\dry_run_pre_news_dual_regime_v1.py` (선택 `docs\final\artifacts\pre_news_bench_inputs_latest.json`)
- 텔레그램: `py scripts\send_pre_news_bridge_stub_telegram_v1.py` — 레포 `.env`의 `TELEGRAM_*` 로드; 없으면 skip
- 자율진화 제안(자동 적용 금지): `py scripts\evolve_pre_news_bench_inputs_v1.py --write-candidate` → `pre_news_bench_evolution_suggestion_latest.json` / `pre_news_bench_inputs_candidate_latest.json`
- 한 번에: `powershell -ExecutionPolicy Bypass -File scripts\run_pre_news_morning_chain_v1.ps1` (`-YfFetch` / `-SkipTelegram` / `-SkipEvolution`)
- 예약 등록: `scripts\register_pre_news_morning_chain_task.ps1` (`-SkipTelegram` 가능)
- 일일 예언 평가 뒤 Pre-News: `powershell -ExecutionPolicy Bypass -File scripts\run_daily_prophecy_then_pre_news_v1.ps1`
- SSH Shadow 실행(원격 체점 + 제안 회수): `powershell -ExecutionPolicy Bypass -File scripts\run_ssh_shadow_pre_news_chain_v1.ps1 -SshHost <host>`
- 로컬 24h 단일 체인(권장): `powershell -ExecutionPolicy Bypass -File scripts\run_local_24h_ops_chain_v1.ps1 -SkipTelegram`
- 로컬 최소 검증 5줄 번들: `powershell -ExecutionPolicy Bypass -File scripts\run_local_min_verification_5lines_v1.ps1`
- 30분 재점검(실전 모드): `powershell -ExecutionPolicy Bypass -File scripts\run_local_live_recheck_30m_v1.ps1`
- 30분 재점검 자동 등록: `powershell -ExecutionPolicy Bypass -File scripts\register_local_live_recheck_30m_task.ps1`
- 모드 전환 가드(실거래/테스트넷 변경 감지): `py scripts\alert_local_trading_mode_transition_v1.py --current-live <true|false> --current-testnet <true|false>`
- 로컬 아침 등록: `scripts\register_local_24h_ops_chain_task.ps1` (`-SkipTelegram`, `-SkipProphecyEval` 선택)
- 주간 후보 검토 패킷: `py scripts\run_pre_news_weekly_candidate_review_v1.py` (수동 승격 전용, 자동 적용 금지)
- 주간 검토 스케줄 등록: `scripts\register_pre_news_weekly_candidate_review_task.ps1`

## 로컬 복구 리허설 6줄 (월 1회 권장)
```powershell
# 1) 데몬 단일화(직접 복제 정리 + 싱글톤 보장)
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\ensure_single_trading_runtime.ps1 -StopDirectCopies -StartSingletonIfMissing

# 2) 메인 로컬 체인 1회 실행(텔레그램 제외)
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_local_24h_ops_chain_v1.ps1 -SkipTelegram

# 3) 최소 검증 리포트 확인(daemon/mode/missing)
py -c "import json,pathlib;d=json.loads(pathlib.Path(r'C:\workspace\reports\local_trading_min_verification_latest.json').read_text(encoding='utf-8'));print(d['daemon']['running'], d['environment']['effective_BTC_ENABLE_LIVE_TRADING'], d['environment']['effective_BTC_TESTNET'], sum(1 for x in d['artifacts'] if not x['exists']))"

# 4) 아침/주간 스케줄러 상태 점검
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'MKM_Local_24H_Ops_Chain','MKM_PreNews_Weekly_Candidate_Review' | Select TaskName,State"

# 5) 주간 리뷰 패킷 1회 수동 생성
py C:\workspace\scripts\run_pre_news_weekly_candidate_review_v1.py

# 6) 핵심 산출물 4종 mtime 확인
py -c "from pathlib import Path;import datetime as dt; fs=[r'C:\workspace\docs\final\artifacts\prophecy_hit_rate_eval_latest.json',r'C:\workspace\docs\final\artifacts\pre_news_dual_regime_bridge_latest.json',r'C:\workspace\docs\final\artifacts\pre_news_bench_evolution_suggestion_latest.json',r'C:\workspace\docs\final\artifacts\pre_news_weekly_candidate_review_latest.json']; [print(f, dt.datetime.utcfromtimestamp(Path(f).stat().st_mtime).isoformat()+'Z') for f in fs]"
```

정상 판정:
- 3번 출력이 `True false true 0`
- 4번 두 태스크 모두 `Ready`
- 6번 네 파일 시간이 현재 시각대에 갱신

## 운영 체크박스 템플릿 (복붙용)
주간/월간 운영 점검 시 아래 블록을 그대로 복사해 사용:

```md
# MKM 로컬 24h 운영 점검 (YYYY-MM-DD)

## A. 모드 고정
- [ ] `BTC_ENABLE_LIVE_TRADING` / `BTC_TESTNET` 값 확인
- [ ] 현재 의도 모드와 일치 (`false/true` 기본)
- [ ] 무단 모드 전환 알림(`local_trading_mode_guard_state.json`) 확인

## B. 일일 체인 헬스
- [ ] `MKM_Local_24H_Ops_Chain` 상태 `Ready`
- [ ] `start_24h_daemon.py` 프로세스 존재
- [ ] `local_trading_min_verification_latest.json`에서 `daemon.running=true`
- [ ] `artifact.missing.count=0`

## C. 주간 후보 리뷰
- [ ] `pre_news_weekly_candidate_review_latest.json` 생성 시각 확인
- [ ] `decision_hint` 확인 (`keep_current` / `manual_compare_required`)
- [ ] 자동 반영 금지 원칙 유지 (`auto_apply_forbidden=true`)

## D. 수동 반영(해당 시만)
- [ ] 승인자 확인 (이름: ________)
- [ ] 반영 전 active/candidate diff 확인
- [ ] 반영 후 즉시 실거래 연결 금지 확인

## E. 월 1회 복구 리허설
- [ ] 런북의 "로컬 복구 리허설 6줄" 실행
- [ ] 판정 기준 3개 충족 확인
- [ ] 결과 로그 보관 경로 기록

## 메모
- 이슈/이상 징후:
- 조치 내용:
- 다음 액션:
```

## Bio Tier-2 운영 1줄 (Curated + Empty Fallback)
- 권장 기본 실행:
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_bio_tier2_preflight_smoke_v1.ps1 -UseCuratedExtraListing -RequireDownloadOk -CuratedMinHitCount 1 -FallbackToRawExtraOnEmptyCurated`
- 의미: 스크리닝→curated 생성→(0건이면 raw extra로 폴백)→merge-only→dry-run smoke 순서로 점검한다.
