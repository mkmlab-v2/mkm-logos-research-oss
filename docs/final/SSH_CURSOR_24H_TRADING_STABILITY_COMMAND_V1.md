# SSH Cursor 24h 매매 안정 운영 명령서 v1

## 0) 적용 원칙 (고정)

- 정책 SSOT: `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md`
- 절차 부록: `docs/final/FINANCIAL_PROPHECY_VPS_LIVE_TRADING_DIRECTIVE_V1.md`
- 고정 분리:
  - 코드/전략 동기화는 상시 수행
  - 실전 주문 ON/OFF는 별도 승인 게이트

## 1) 로컬 선행 확인 (이미 확인됨)

- 현재 브랜치: `chore/orchestration-gate-runbook-lock`
- 추적 원격: `origin/chore/orchestration-gate-runbook-lock`
- 상태: **ahead 없음 (추가 push 불필요)**

## 2) SSH Cursor에 붙여넣을 지시문 (복붙용)

```text
[목표]
VPS 본선을 최신 코드/전략으로 동기화하고, 24시간 운영 안정성(경로/상태/가드)을 확인한다.
주의: 동기화와 실전 주문 활성화는 분리한다. 주문 ON/OFF는 승인 게이트 없이는 바꾸지 않는다.

[필수 절차]
1) 본선 경로 실측
- pm2 show bitcoin-live (또는 실제 앱 이름)
- 출력에서 exec cwd와 script path를 보고 REPO_ROOT를 확정
- 이후 모든 작업은 cd REPO_ROOT에서만 실행

2) Git 동기화 (REPO_ROOT)
- git status
- git fetch --all --prune
- git pull --ff-only
- git rev-parse --short HEAD
- 중간에 로컬 변경이 있으면 중단하고 보고

3) Fact-Safe 리스크 프로파일 동기화 (REPO_ROOT)
- python3 scripts/sync_fact_safe_risk_profile.py --prophecy docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json --output projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json --integrated-governance docs/final/artifacts/integrated_governance_v1_latest.json
- python3 -c "import json; p='projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json'; d=json.load(open(p,encoding='utf-8')); print({'source':d.get('source'),'mode':d.get('mode'),'generated_at':d.get('generated_at')})"

4) 런타임 반영 (단일 앱만)
- pm2 restart bitcoin-live (또는 실제 앱 이름 1개)
- pm2 status
- pm2 logs bitcoin-live --lines 120
- 절대 금지: pm2 restart all

5) 24h 안정 운영 점검 리포트 (요약 5줄)
- REPO_ROOT
- 현재 커밋 해시
- risk_profile source/mode/generated_at
- PM2 단일 앱 online 상태
- 오류/경고 유무 및 즉시 조치 필요 항목

6) 승격 아티팩트 기준(운영 보고에 반드시 포함)
- docs/final/artifacts/control_tower_latest.json: promotion_readiness.status
- docs/final/artifacts/promotion_preflight_v1_latest.json: result
- docs/final/artifacts/a_track_go_nogo_status_latest.json: overall_go_no_go, recommended_stage
- docs/final/artifacts/trackb_weekly_gate_recheck_latest.json: decision
- reports/constitution/btrack_pilot/btrack_promotion_gate_latest.json: decision
- docs/final/artifacts/dual_promotion_prep_pack_latest.json: blocking_items
- docs/final/artifacts/ssot_recovery_evidence_snapshot_latest.json: 최신 스냅샷 존재 여부

7) 24h 하드라인 게이트(실전 차단 기준)
- max_drawdown <= -3.0% 또는 연속 손실 >= 4회면 즉시 cooldown
- 주문 ACK p95 > 1500ms가 10분 지속되면 신규주문 차단
- API 실패율 > 5%가 5분 지속되면 신규주문 차단
- state mismatch 1건 이상이면 즉시 신규주문 차단
- 자동 재개 금지: 최소 30분 + health 15분 정상 + 승인 플래그

[중요 가드]
- 실전 주문 활성화(ON/OFF) 변경 명령은 실행하지 말고 승인 요청으로 분리
- 본선 경로가 불확실하면 어떤 파일도 수정/재시작하지 말고 즉시 보고
- B-track 결과는 research_only/no auto-bind 원칙을 깨지 않는다
```

## 3) 운영자 확인 체크 (짧게)

- SSH 결과 보고에서 `REPO_ROOT`, `HEAD`, `risk_profile` 3항목이 모두 갱신됐는지 확인
- 주문 활성화 관련 변경이 없었는지 확인
- 이상 징후가 있으면 `observe/shadow` 유지 후 원인 분리

