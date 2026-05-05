# jemaai.cloud — 공개 쇼룸 vs 비공개 관제 (하이브리드 대시보드)

**목적**: “전광판(공개)”과 “조종실(비공개)”을 분리해 **마케팅·신뢰**와 **실매매·민감정보**를 동시에 지킨다.  
**구현 팩트**: 공개 API는 `public_event_gateway.py` (`schema_version`: `public-event.v1`). nginx 예시·기동은 동일 디렉터리의 `nginx_public_event_gateway.conf.example`, `ensure_public_event_gateway.ps1`(상위 `ops`).

**관련 정책(모노레포 루트):** 랜딩·호스트 키·과장 표현 등 **전 채널 공통** 점검은 `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` — 본 SPEC은 공개 이벤트 스키마·지연·면책 수치에 특화되어 있으며, Track C 상용 경계는 `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` 와 정합한다.

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

- **쇼룸 UX (연출 계약, ASCII만)** — 번들 빌더가 기본 채움; ingest에서 덮어쓸 수 있음(화이트리스트 브릿지 경유).
  - `showroom_display_mode`: `idle` \| `defend` \| `attack` — 픽셀/티커 모드의 **서버 기준** 표현(실매매 트리거 아님).
  - `showroom_ticker_key`: 대문자·숫자·밑줄만 `^[A-Z0-9_]{1,64}$` — 짧은 기계 키; 한글 카피는 `public_showroom_poll.html` 매핑 또는 공백 치환 표시.
  - `showroom_reaction_line_ids`: 문자열 배열 **최대 3개**, 각 원소 `^R_[A-Z0-9_]{1,32}$` — 가상 채팅용 **ID**(원문 자유 텍스트 금지 → 면책·스팸 방지); UI에서 한글 라인으로 매핑.
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
- **E2E 스모크(운영 직전)**: `..\run_jemaai_public_event_e2e_smoke.ps1` (profiles endpoint + ingest→latest ID 정규화 검증)
- **curl (로컬)** — 토큰은 환경변수만:

```text
curl -sS -X POST "http://127.0.0.1:8788/api/public-events/ingest" -H "Content-Type: application/json" -H "X-Public-Event-Token: %PUBLIC_EVENT_GATEWAY_TOKEN%" -d "@examples/public_event_ingest_minimal.v1.json"
```

(`jemaai-cloud-mvp` 디렉터리에서 상대 경로 기준.)

- **정적 쇼룸 샘플**: `public_showroom_poll.html` — `GET .../latest` 폴링·표시. 하단 **Information** 섹션에 `data-disclaimer-ref="jemaai_showroom_v1"` 고지 고정(본 문서 §3 면책과 정합).

### 4.2 Showroom bundle (레포 자동화, v1)

- **Track C 원클릭 체인 (권장):** `scripts/build_showroom_track_c_bundle_chain_v1.ps1` — (1) `build_logos_track_c_freshness_sidecar_v1.py`로 신선도 사이드카 갱신 → (2) `build_showroom_display_bundle.ps1` → (3) `validate_showroom_public_bundle.py`. 선택: `-SkipFreshnessSidecar`, `-SkipValidate`.
- **빌더 (단독):** `projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1` — C2·퓨전·런타임 헬스에서 `public-event.v1` 페이로드 + `observability` 메타를 합성한다(Logos 그래프 메타·신선도 필드는 디스크의 최신 아티팩트를 읽음).
- **산출:** `docs/final/artifacts/showroom_public_bundle_v1.json` (SSOT), `jemaai-cloud-mvp/showroom_public_bundle_v1.json` (웹 루트 배포본과 동기화).
- **검증:** `scripts/validate_showroom_public_bundle.py` — 필수 키·면책 ref·공개 레인 민감 토큰 차단.
- **퓨전 사이클:** `run_ops_fusion_cycle.ps1` 종료 시 빌드·검증을 함께 수행한다.
- **게이트웨이 반영(선택):** `publish_showroom_public_event.ps1`로 ingest POST. 퓨전 사이클과 함께 쓰려면 `SHOWROOM_PUBLISH_INGEST=1`(User/Process).
- **정적 파일 복사(선택):** `deploy_showroom_static.ps1` — `-WebRoot` 또는 `JEMAAI_WEB_ROOT`에 HTML·JSON 복사 후 본선에서 nginx reload. 둘 다 비어 있으면 기본으로 `ops/windows-rehearsal/.showroom_staging/`(gitignore)에 복사해 로컬 확인·rsync 소스로 사용.
- **VPS scp 원클릭:** 루트 `scripts/sync_showroom_to_vps.ps1` → `projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1`. `.showroom_staging`의 정적 2파일을 `MKM_VPS_HOST`/`MKM_VPS_USER` 및 `JEMAAI_VPS_SHOWROOM_ROOT`(기본 `/var/www/jemaai`)로 전송; **`-RefreshStaging`은 Track C 체인(`build_showroom_track_c_bundle_chain_v1.ps1`) + `deploy_showroom_static.ps1` 후 scp.**
- **`public_ui` (`showroom_public_ui_v1`):** ASCII 기계값만(방향·램프·융합·수익률 유무). 한글 카피는 `public_showroom_poll.html`에서 매핑한다(PS 인코딩 이슈 회피).
- **방향 소스:** 환경 `SHOWROOM_DIRECTION_SOURCE=c2|account` 미설정 시 **auto** — `public_trading_metrics_latest.json`에 `position_side`가 있으면 `account`(롱/숏 추상만), 없으면 `c2`.

### 4.3 Gemini 환경 (GOOGLE_API_KEY 레거시 경고 정리)

`GEMINI_API_KEY`만 쓸 때 사용자 환경의 **`GOOGLE_API_KEY`** 가 남아 있으면 중복 경고가 날 수 있다 → 사용자 환경에서 제거. 힌트: `scripts/print_gemini_env_hygiene_hint.ps1` (레포 루트 `scripts`).

---

## 5. 한 줄 요약

**jemaai.cloud = 전광판**, **실매매 = 조종실** — 공개 채널에는 **허용 필드만** 올린다.
