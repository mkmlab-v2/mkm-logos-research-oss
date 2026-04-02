# jemaai.cloud — 공개 쇼룸 vs 비공개 관제 (하이브리드 대시보드)

**목적**: “전광판(공개)”과 “조종실(비공개)”을 분리해 **마케팅·신뢰**와 **실매매·민감정보**를 동시에 지킨다.  
**구현 팩트**: 공개 API는 `public_event_gateway.py` (`schema_version`: `public-event.v1`). nginx 예시·기동은 동일 디렉터리의 `nginx_public_event_gateway.conf.example`, `ensure_public_event_gateway.ps1`(상위 `ops`).

---

## 1. 역할 구분

| 구역 | 대상 | 허용되는 것 |
|------|------|-------------|
| **공개 쇼룸** (jemaai.cloud) | 방문자·투자자 | 가동 여부, 지연·추상화된 신호, 테마·방향(Long/Short 등), **비식별** 수익률 |
| **비공개 관제** (인증 대시보드·VPS·로컬) | 지휘관·운용 | 주문·체결·잔고·레버리지·API 상태·긴급 정지 |

**금지**: 공개 URL에 API 키, 정확한 포지션 크기·진입가·거래소 계정 식별자, 실시간 무지연 PnL 원시값(정책 미검토 시).

---

## 2. 게이트웨이 페이로드 (`public-event.v1`)

`POST /api/public-events/ingest`는 아래 **필수 키**를 만족해야 한다(코드: `_is_valid_event`).

- `timestamp`, `active_character_id`, `risk_level`, `public_signal_direction`, `abstract_reason`, `schema_version`, `event_id`, `source`

**권장(선택 키)** — 프론트가 쓰면 쇼룸만 풍성해지고, 관제 데이터와 분리 유지:

- `system_status`: 예) `online` | `degraded` | `maintenance`
- `active_strategies_count`: 숫자(추상)
- `delayed_metrics`: 예) `{ "delay_seconds": 120, "pnl_pct_vs_start": 12.4, "as_of_utc": "..." }` — **금액 대신 %** 권장
- `direction_abstract`: 예) `long` | `short` | `flat` (가격·수량 없음)
- `disclaimer_ref`: 면책·기준 자산 문구의 고정 ID 또는 짧은 문자열

선택 키는 **백엔드가 민감 데이터를 넣지 않도록** 별도 변환 레이어에서만 채운다.

---

## 3. 지휘관 결정(경계선) — 스펙 확정 전 체크

| 결정 항목 | 권장 방향 |
|-----------|-----------|
| **지연** | 공개 PnL·상태는 1~5분 지연 또는 “최근 스냅샷 시각” 명시 |
| **금액 vs 수익률** | 공개는 **%·테마** 위주; 절대 금액은 비공개 또는 모호화 |
| **장애 시** | 마지막 값 고정보다 `system_status=maintenance` + `last_ok_utc` 권장 |
| **면책** | 기준 자산·기간·갱신 주기를 UI 또는 `disclaimer_ref`로 고정 |

---

## 4. 운영 연결

- **인입**: n8n·브릿지가 **필터링된** JSON만 `ingest`로 POST (`X-Public-Event-Token` = `PUBLIC_EVENT_GATEWAY_TOKEN`).
- **조회**: 프론트는 `GET /api/public-events/latest` 폴링(또는 별도 WS는 프록시 뒤에서만).
- **실매매 엔진**은 이 게이트웨이와 **직접 동일 프로세스로 묶지 않는다** — 항상 **추출·지연·화이트리스트** 레이어를 경유.

---

## 5. 한 줄 요약

**jemaai.cloud = 전광판**, **실매매 = 조종실** — 공개 채널에는 **허용 필드만** 올린다.
