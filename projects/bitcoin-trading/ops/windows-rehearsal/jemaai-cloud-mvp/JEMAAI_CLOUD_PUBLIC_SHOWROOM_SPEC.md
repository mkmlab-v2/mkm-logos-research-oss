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

- **정적 쇼룸 샘플**: `public_showroom_poll.html` — `GET .../latest` 폴링·표시(스테이지·예능 레이어 포함). 하단 **Information** 섹션에 `data-disclaimer-ref="jemaai_showroom_v1"` 고지 고정(본 문서 §3 면책과 정합).
- **정적 쇼룸(미니멀 보드, 권장 공개면)**: `public_showroom_board_minimal.html` — 동일 API·동일 티커/반응 ID 매핑 계약; WebGL/픽셀 스테이지 없음. 배포·scp는 `deploy_showroom_static.ps1` / `sync_showroom_to_vps.ps1`에 포함.

### 4.2 Showroom bundle (레포 자동화, v1)

- **Track C 원클릭 체인 (권장):** `scripts/build_showroom_track_c_bundle_chain_v1.ps1` — (1) `build_logos_track_c_freshness_sidecar_v1.py`로 신선도 사이드카 갱신 → (2) `build_showroom_topology_radar_snapshot_v1.py`로 Topology Radar 스냅샷(`docs/final/artifacts/showroom_topology_radar_snapshot_v1_latest.json`; 기본 스텁 ref 허용, 엄격 모드 `-TopologyRadarSnapshotStrict`) → (3) `build_showroom_display_bundle.ps1` → (4) `validate_showroom_public_bundle.py`. 선택: `-SkipFreshnessSidecar`, `-SkipTopologyRadarSnapshot`, `-SkipValidate`.
- **빌더 (단독):** `projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1` — C2·퓨전·런타임 헬스에서 `public-event.v1` 페이로드 + `observability` 메타를 합성한다(Logos 그래프 메타·신선도 필드는 디스크의 최신 아티팩트를 읽음). **Topology Radar:** `showroom_topology_radar_snapshot_v1_latest.json`이 계약을 만족하면(`no_trade_signals: true`) `observability.topology_radar_snapshot_*` 요약을 병합한다(경로만 `sources`에 기록).
- **산출:** `docs/final/artifacts/showroom_public_bundle_v1.json` (SSOT), `jemaai-cloud-mvp/showroom_public_bundle_v1.json` (웹 루트 배포본과 동기화).
- **검증:** `scripts/validate_showroom_public_bundle.py` — 필수 키·면책 ref·공개 레인 민감 토큰 차단.
- **퓨전 사이클:** `run_ops_fusion_cycle.ps1` 종료 시 빌드·검증을 함께 수행한다.
- **게이트웨이 반영(선택):** `publish_showroom_public_event.ps1`로 ingest POST. 퓨전 사이클과 함께 쓰려면 `SHOWROOM_PUBLISH_INGEST=1`(User/Process).
- **정적 파일 복사(선택):** `deploy_showroom_static.ps1` — `-WebRoot` 또는 `JEMAAI_WEB_ROOT`에 HTML·JSON 복사 후 본선에서 nginx reload. 둘 다 비어 있으면 기본으로 `ops/windows-rehearsal/.showroom_staging/`(gitignore)에 복사해 로컬 확인·rsync 소스로 사용. **Topology Radar 스냅샷** `showroom_topology_radar_snapshot_v1_latest.json`은 `docs/final/artifacts`에 있으면 동명으로 스테이징에 복사(없으면 경고 후 생략).
- **VPS scp 원클릭:** 루트 `scripts/sync_showroom_to_vps.ps1` → `projects/bitcoin-trading/ops/windows-rehearsal/sync_showroom_to_vps.ps1`. `.showroom_staging`의 정적 파일(HTML·번들·**선택: topology 스냅샷**)을 `MKM_VPS_HOST`/`MKM_VPS_USER` 및 `JEMAAI_VPS_SHOWROOM_ROOT`(기본 `/var/www/jemaai`)로 전송; **`-RefreshStaging`은 Track C 체인(`build_showroom_track_c_bundle_chain_v1.ps1`) + `deploy_showroom_static.ps1` 후 scp.**
- **`public_ui` (`showroom_public_ui_v1`):** ASCII 기계값만(방향·램프·융합·수익률 유무). 한글 카피는 `public_showroom_poll.html`에서 매핑한다(PS 인코딩 이슈 회피).
- **방향 소스:** 환경 `SHOWROOM_DIRECTION_SOURCE=c2|account` 미설정 시 **auto** — `public_trading_metrics_latest.json`에 `position_side`가 있으면 `account`(롱/숏 추상만), 없으면 `c2`.
- **본선 nginx 반영(권장 체크리스트, 호스트 수동):** (1) `jemaai-cloud-mvp/nginx_snippets/jemaai_showroom_ui.conf`를 해당 `server { ... }` 안에 `include`(경로는 배포 표준에 맞게 조정). (2) 스니펫에 **`location = /showroom_topology_radar_snapshot_v1_latest.json`** 블록이 포함돼 있는지 확인(없으면 동 파일 기준으로 추가). (3) 정적 파일을 `/var/www/jemaai/` 등 웹 루트에 배치한 뒤 `sudo nginx -t && sudo systemctl reload nginx`. (4) 검증: `curl -sSI https://<공개호스트>/showroom_topology_radar_snapshot_v1_latest.json` → `200` 및 `cache-control: no-store`(또는 동등) 권장; 동일 방식으로 `showroom_public_bundle_v1.json` 확인.

### 4.3 Gemini 환경 (GOOGLE_API_KEY 레거시 경고 정리)

`GEMINI_API_KEY`만 쓸 때 사용자 환경의 **`GOOGLE_API_KEY`** 가 남아 있으면 중복 경고가 날 수 있다 → 사용자 환경에서 제거. 힌트: `scripts/print_gemini_env_hygiene_hint.ps1` (레포 루트 `scripts`).

### 4.4 Topology Radar / Meaning-graph 슬롯 (Track C §3.6 확장, 2026-05)

**목적:** `docs/final/TRACK_C_TOPOLOGY_RADAR_SHOWROOM_BLUEPRINT_V1.md` 청사진과 동일 프레임으로, **다차원 텍스트 위상 관측**을 공개 쇼룸에 **읽기 전용**으로 붙인다. 성경·Logos 축은 **해설·가설(`[HYPO]`)**이며 **실매매·주문·실키와 합선하지 않는다** (`AGENTS.md` 렌즈 계약, Track C §1·§9).

| 차원 | 규칙 |
|------|------|
| **입력** | Track B·로컬 체인이 이미 기록한 **경로 고지 산출물**만(예: `logos_corpus_graph_bundle_v1_latest.json`, Logos 신선도 사이드카, Aramaic MVP 체인의 **공개 가능 메타**). 원문 코퍼스·전체 파이프라인·가중치는 **공개면에 올리지 않는다**. |
| **스냅샷 계약** | `docs/final/schemas/showroom_topology_radar_snapshot_v1.schema.json` + example — 필수 `no_trade_signals: true`, `disclaimer_ref`는 §3 표와 동일 계열(`jemaai_showroom_v1` 등)로 맞춘다. |
| **출력** | 정적 HTML·폴링 JSON 또는 `public-event.v1` **선택 확장 필드**로만 반영한다. **매수·매도·레버리지·실행 지시** 문구·필드 **금지**. |
| **금지 응답** | “내일 오른다/내린다”, 확정 예언, 알파 보장, 의료·종교 단정, NotebookLM·채팅 브리핑만의 구현 완료 주장. |
| **배선** | 1차: `build_showroom_track_c_bundle_chain_v1.ps1`가 `showroom_topology_radar_snapshot_v1_latest.json`을 emit한 뒤 `showroom_public_bundle_v1.json` 경로와 병행해 스냅샷만 별도 정적 자산으로 두어도 된다(게이트웨이와 **직접 주문 결합 금지**는 본 SPEC §1·§6과 동일). |

**Fact-Lock:** 구현·게이트 경로는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 `scripts/verify_p0_constitution_gate_paths.ps1`와 동기 후 확장한다.

### 4.5 Phase 2.1 — Risk Topology Radar UI (Showroom, 2026-05-16)

**페이지:** `public_showroom_topology_radar_v1.html` — 정적 JSON + 선택 API 폴링. **매매·투자 권유·실행 지시 금지.**

| 입력 | 필드 / 소스 | UI 매핑 |
|------|-------------|---------|
| Topology 스냅샷 | `showroom_topology_radar_snapshot_v1_latest.json` (`summary_one_line`, `hypo_banner`, `disclaimer_ref`, `no_trade_signals`) | 요약·배지·면책 |
| 공개 번들 | `showroom_public_bundle_v1.json` → `public_event_v1` | `showroom_display_mode`, `risk_level`, `system_status`, `delayed_metrics` |
| (선택) 라이브 | `GET {api}/api/public-events/latest` | 번들 이벤트와 동일 화이트리스트 필드만 |

| 레이더 상태 | 조건 (우선순위) | 시각 |
|-------------|-------------------|------|
| **calm** | `risk_level` ∈ {INFO, SAFE} · `showroom_display_mode` = idle | 녹색/은은 맥동 |
| **watch** | `risk_level` = WARNING · 또는 `showroom_display_mode` = defend | amber 맥동 |
| **critical** | `risk_level` = CRITICAL · 또는 `showroom_display_mode` = attack | red 맥동 (관측·게이트 인지, 매매 신호 아님) |

### 4.6 Phase 2.2 — Logos deep dive panel (Showroom, 2026-05-16)

**트리거:** `public_showroom_topology_radar_v1.html` 레이더 **중심(core)** 또는 **WATCH/critical 링(ring-pulse)** 클릭·키보드(Enter/Space).

| 입력 | 소스 | 패널 |
|------|------|------|
| 연구 슬라이스 | `showroom_logos_research_slice_v0.json` (동 디렉터리 · `api.jemaai.cloud` · 빌드: `build_showroom_logos_research_slice_v1.py`) | 테마 1건 + semantic nodes 최대 4 · commander insight 요약 |
| 레이더 상태 → 테마 | `critical` → `theme_08_seal_mark` · `watch` → `theme_02_fact_lock_gate` · `calm` → `theme_06_exodus_regime_passover` | 상태별 상징 해설 (운영 매핑 아님) |

**고정 배지:** `[HYPO]` · `research_only` · `NON_GATING` · 전체 목록 링크 `public_showroom_logos_research_v1.html`.

**금지:** 패널·링크 copy를 실매매·Track A 게이트·매수/매도 신호로 읽히게 표기하지 않는다.

**배포:** `deploy_showroom_static.ps1` · nginx `location = /public_showroom_topology_radar_v1.html` (`nginx_snippets/jemaai_showroom_ui.conf`).

---

## 5. 한 줄 요약

**jemaai.cloud = 전광판**, **실매매 = 조종실** — 공개 채널에는 **허용 필드만** 올린다.

---

## 6. Edge Zero-Trust (2026 권장): Tunnel + GET HMAC

**목적:** Vercel(또는 기타 프런트) ↔ VPS 게이트웨이 사이를 **인바운드 포트 노출 없이** 연결하고, 터널 안에서도 **읽기 요청을 서명으로 한 번 더 증명**한다.

| 레이어 | 권장 |
|--------|------|
| **네트워크** | Hostinger VPS에서 **Cloudflare Tunnel**(`cloudflared`)만 아웃바운드로 연결. 공인 IP에 `8788` 등을 직접 바인딩하지 않으면 스캐너의 표면이 줄어든다. nginx는 루프백 `127.0.0.1:8788`만 `proxy_pass`(기존 `nginx_public_event_gateway.conf.example`). |
| **애플리케이션 (GET)** | VPS 프로세스에 `PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET`을 두면 `GET /api/public-events/latest`는 **`x-mkm-timestamp`(unix 초)** + **`x-mkm-signature`(hex HMAC-SHA256)** 필수. Canonical 문자열은 코드와 동일: `"{ts}\\nGET\\n/api/public-events/latest\\n"`. 허용 시각 편차는 `PUBLIC_EVENT_GATEWAY_HMAC_MAX_SKEW_SEC`(기본 300초). 비밀이 **비어 있으면** 기존과 같이 GET은 무인증(하위 호환). |
| **쓰기 격벽** | 실매매·강제 조작은 이 게이트웨이로 **보내지 않는다**. `POST /ingest`는 기존대로 브릿지·n8n·토큰 경로만 사용하고, UI에서 **주문 ON/OFF** 같은 위험 액션은 SSH·내부 승인 경로로만 둔다(본 SPEC §1·루트 운영 원칙과 동일). |

**로컬 서명 예시(비밀은 환경변수만):** `py scripts/sign_public_event_gateway_get_hmac_v1.py` — 출력 헤더를 curl에 붙여 검증.

**Fact-Lock:** 구현·헤더 계약은 `public_event_gateway.py` · 회귀 `tests/test_public_event_gateway_get_hmac_v1.py` · `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` Public Event Gateway 행.
