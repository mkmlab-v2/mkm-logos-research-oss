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

## 3. 지휘관 결정(경계선) — **확정값 (2026-04)**

공개 쇼룸·ingest·프론트가 **동일 숫자·문구**를 쓰도록 고정. 변경 시 본 절 개정일 또는 `schema_version`을 올린다.

| 결정 항목 | 확정 |
|-----------|------|
| **지연(의도)** | 실시간 대비 **최소 120초(2분)**, **기본 180초(3분)**, **상한 300초(5분)**. `delayed_metrics.delay_seconds`는 이 구간에서만. 공개 UI에 “실시간” 표현 **금지**. |
| **스냅샷 시각** | `delayed_metrics.as_of_utc`(권장, ISO8601 UTC)와 `timestamp`로 기준 시각 항상 표기 가능. |
| **금액 vs 수익률** | 공개: **%·방향·테마만** (`pnl_pct_vs_start`, `direction_abstract`). **절대 통화 금액·노셔널·잔고·거래소 UID·API 키**는 ingest·UI **금지**. |
| **장애 시** | `system_status`: `online` \| `degraded` \| `maintenance`. 장애 시 **마지막 유효 페이로드 유지** + **`last_ok_utc`(ISO8601 UTC)** 필수. |
| **면책** | `disclaimer_ref` 고정: **`jemaai_showroom_v1`**. UI 하단에 과거 성과·지연·비투자조언 문구 고정. |

---

## 4. 운영 연결

- **인입**: n8n·브릿지가 **필터링된** JSON만 `ingest`로 POST (`X-Public-Event-Token` = `PUBLIC_EVENT_GATEWAY_TOKEN`).
- **조회**: 프론트는 `GET /api/public-events/latest` **폴링 권장 15~60초**(공개 지연과 합산 시 체감 지연 증가). WS는 프록시 뒤에서만.
- **실매매 엔진**은 이 게이트웨이와 **동일 프로세스로 직접 묶지 않는다** — **추출·지연·화이트리스트** 경유.

### 4.1 n8n·배치 브릿지 (민감값 제거 후)

- 워크플로 끝에 **화이트리스트** Function: 허용 키만 통과. 주문·잔고·키·원시 시세 **금지**.
- **예시 JSON**: `examples/public_event_ingest_minimal.v1.json`
- **n8n Function 템플릿**: `examples/n8n_public_event_whitelist_function.js` (ID 정규화 + 지연/리스크 안전값 고정)
- **curl (로컬)** — 토큰은 환경변수만:

```text
curl -sS -X POST "http://127.0.0.1:8788/api/public-events/ingest" -H "Content-Type: application/json" -H "X-Public-Event-Token: %PUBLIC_EVENT_GATEWAY_TOKEN%" -d "@examples/public_event_ingest_minimal.v1.json"
```

(`jemaai-cloud-mvp` 디렉터리에서 상대 경로 기준.)

- **정적 쇼룸 샘플**: `public_showroom_poll.html` — `GET .../latest` 폴링·표시.

### 4.2 Gemini 환경 (GOOGLE_API_KEY 레거시 경고 정리)

`GEMINI_API_KEY`만 쓸 때 사용자 환경의 **`GOOGLE_API_KEY`** 가 남아 있으면 중복 경고가 날 수 있다 → 사용자 환경에서 제거. 힌트: `scripts/print_gemini_env_hygiene_hint.ps1` (레포 루트 `scripts`).

---

## 5. 한 줄 요약

**jemaai.cloud = 전광판**, **실매매 = 조종실** — 공개 채널에는 **허용 필드만** 올린다.
