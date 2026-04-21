# SSH Cursor Command Sheet (Limited Live)

## 0) 목적
- 현재 승인 상태(`limited_live_deployment`)를 SSH/VPS 운영에 반영한다.
- 기존 메인 전략은 유지하고, fast-gate 신호는 제한적 병렬 라우트로 운용한다.

## 1) 서버 접속 후 기본 동기화
```bash
cd /path/to/your/repo
git fetch --all --prune
git pull --ff-only origin main
```

## 2) 승인/게이트 아티팩트 확인
```bash
python scripts/fast_promotion_gate_v1.py
python scripts/build_a_track_go_nogo_status.py
```

확인 포인트:
- `docs/final/artifacts/fast_promotion_gate_v1_latest.json`:
  - `result.live_ready == true`
- `docs/final/artifacts/a_track_go_nogo_status_latest.json`:
  - `result.overall_go_no_go == "HOLD"`
  - `result.recommended_stage == "S1_SHADOW"`

## 3) 제한적 라이브 전용 신호 재생성
```bash
python scripts/build_btrack_prophecy_score_from_ohlcv.py \
  --btc-csv research/market_data/btc_daily_external_yf.csv \
  --recent-trading-days 30

python scripts/eval_prophecy_hit_rate_v1.py \
  --run-mode price \
  --score-json docs/final/artifacts/btrack_prophecy_score_latest.json
```

## 4) 병렬 운용 원칙 (핵심)
- 기존 메인 실거래 전략은 유지한다.
- fast-gate 신호는 별도 소액 라우트(병렬)로만 투입한다.
- A-track 글로벌 HOLD가 풀리기 전에는 메인 라우트 대체 금지.

## 5) 롤백 트리거
- 게이트 FAIL (`live_ready=false`)
- 무결성 경고/입력 누락
- 운영자 중지 명령

롤백 시:
```bash
# 제한 라우트 중지(운영 환경에 맞는 pm2 이름 사용)
pm2 stop <limited-live-process-name>
pm2 logs <limited-live-process-name> --lines 200
```

## 6) 참고 아티팩트
- `docs/final/artifacts/promotion_signoff_decision_latest.json`
- `docs/final/artifacts/promotion_signoff_brief_latest.md`
- `docs/final/artifacts/dual_promotion_prep_pack_latest.json`
