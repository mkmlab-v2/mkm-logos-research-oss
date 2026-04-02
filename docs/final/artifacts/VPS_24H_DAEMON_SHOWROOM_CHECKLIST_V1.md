# VPS 24h Daemon + Showroom 연동 체크리스트 v1

목표: **비공개 실매매(조종실)**와 **공개 12AI 쇼룸(전광판)**을 분리한 채 24시간 운영한다.  
원칙: 본선 매매는 VPS에서만, 공개 채널은 `public-event.v1` 허용 필드만 노출한다.

---

## 0) 아키텍처 (고정)

1. **VPS/본선**: 트레이딩 데몬 상시 실행
2. **브릿지 레이어**: 민감값 제거 + 지연(2~5분) + 화이트리스트
3. **공개 게이트웨이**: `public_event_gateway.py` ingest/latest 제공
4. **쇼룸/방송**: latest 폴링 화면(`public_showroom_poll.html` 등)

---

## 1) 사전 점검

- [ ] `projects/bitcoin-trading/src/daemon/bitcoin_trading_daemon.py` 존재
- [ ] `projects/bitcoin-trading/scripts/start_24h_daemon.py` 존재
- [ ] `projects/bitcoin-trading/ops/windows-rehearsal/ensure_daemon_running.ps1` 존재
- [ ] `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_event_gateway.py` 존재
- [ ] `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/examples/public_event_ingest_minimal.v1.json` 존재
- [ ] `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/examples/n8n_public_event_whitelist_function.js` 존재

---

## 2) 본선 24h 데몬 (VPS)

1. 데몬 단일 인스턴스 보장:
   - [ ] 중복 프로세스 정리 후 1개만 유지
2. 데몬 시작:
   - [ ] `start_24h_daemon.py` 또는 운영 스크립트로 기동
3. 상태 확인:
   - [ ] `trading_state.json`에서 `running=true` 확인
   - [ ] runtime health/guard 로그에서 오류 없음 확인

권장: watchdog/재기동 태스크와 함께 배포.

---

## 3) 공개 게이트웨이 (쇼룸 전용)

1. 게이트웨이 기동:
   - [ ] `public_event_gateway.py` 서비스 활성
2. 보호:
   - [ ] `PUBLIC_EVENT_GATEWAY_TOKEN` 설정
   - [ ] nginx 리버스 프록시 설정(`nginx_public_event_gateway.conf.example`)
3. 헬스체크:
   - [ ] `/healthz` 또는 동등 엔드포인트 200 확인

---

## 4) 데이터 위생 (필수)

공개 이벤트는 아래만 허용:
- `timestamp`, `active_character_id`, `risk_level`, `public_signal_direction`, `abstract_reason`, `schema_version`, `event_id`, `source`
- 선택: `system_status`, `active_strategies_count`, `delayed_metrics`, `direction_abstract`, `disclaimer_ref`

금지:
- API 키/토큰 원문
- 정확 포지션 수량·진입가·계정 식별자
- 무지연 원시 PnL/잔고/주문 원장

---

## 5) 쇼룸/방송 연동

1. 인입:
   - [ ] n8n Function 화이트리스트(`n8n_public_event_whitelist_function.js`) 적용
   - [ ] `POST /api/public-events/ingest` 정상 응답 확인
2. 표시:
   - [ ] `GET /api/public-events/latest` 폴링 정상
   - [ ] 방송 오버레이(쇼룸 UI)에서 방향/상태/지연 정보만 노출

---

## 6) 검증 커맨드 (로컬/운영 공통)

```powershell
# 게이트웨이 E2E 스모크
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_jemaai_public_event_e2e_smoke.ps1"

# 공개 ingest 최소 예시
curl -sS -X POST "http://127.0.0.1:8788/api/public-events/ingest" -H "Content-Type: application/json" -H "X-Public-Event-Token: %PUBLIC_EVENT_GATEWAY_TOKEN%" -d "@examples/public_event_ingest_minimal.v1.json"
```

---

## 7) 롤백 절차

문제 발생 시 즉시:

1. [ ] 공개 ingest 중단 (토큰 교체 또는 수신 차단)
2. [ ] 쇼룸은 마지막 정상 이벤트 표시 + `system_status=degraded/maintenance`
3. [ ] 본선 데몬은 유지하되, 필요 시 `enable_trading=false` 안전 모드 전환
4. [ ] 원인 해결 후 E2E 스모크 통과 시 재개

---

## 8) 운영 판단 기준 (Go/No-Go)

- **GO**:
  - 데몬 단일 인스턴스 안정
  - 게이트웨이 헬스 200
  - 화이트리스트 적용 확인
  - 공개 데이터에 민감 정보 미포함
- **NO-GO**:
  - 데몬 중복 실행/비정상 종료 반복
  - 공개 payload에 민감 필드 유출
  - 게이트웨이 인증/헬스 실패

---

## 한 줄 결론

**실매매는 VPS에서 24h, 공개는 지연·비식별 이벤트만 쇼룸으로 송출** — 두 레인을 물리적으로 분리하면 12AI 방송 연동이 안전하게 가능하다.

