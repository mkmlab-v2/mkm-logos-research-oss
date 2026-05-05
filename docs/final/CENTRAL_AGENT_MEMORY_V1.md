# Central agent memory v1 (cross-chat SSOT)

**목적:** 채팅은 맥락을 공유하지 않는다. 본 파일은 **Athena 정체성 + 이론 지문(고효율 압축) + 최소 진행 표**만 둔다.  
**구분:** `CURRENT_OPS_SNAPSHOT.md` = 일시 핸드오프 · 본 파일 = **지속·정체성 SSOT**(짧게 유지).

## 메타

- **schema:** `central_agent_memory_v1`
- **last_updated_utc:** 2026-05-05T07:21:27Z
- **owner:** (선택)
- **nl_sync:** `cross_notebook_query` · MKM·운영 노트북 15종 · 코퍼스 기간은 NL에 보이는 노트 생성일 기준 **2026-01~04** (2025 노트북은 목록에 없음) · **2026-04-19** `sync_notebooklm_sources_to_mkm_data_vault.ps1` → Vault `notebooklm_sources` **OK**(복사 50; 매니페스트상 누락·optional 스킵은 정책대로 WARNING/회색 스킵) · **2026-04-28** NotebookLM MCP `server_info/notebook_list` live 확인(auth configured, owned notebooks 11, TOP1/TOP2/ Fusion Hub 포함) · **2026-05-05** 동 스크립트 재실행 **exit 0** `copied=104 skipped=91` → `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources` **OK**; 구현 계약 **메타 인지 봉투 v1**은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§1.3.1**·`scripts/mkm_meta_layer_envelope_v1.py`·회귀 pytest 8·Track C `-MetaLayerEnvelopePath`(비면 미실행)로 Fact-Lock 고정(NotebookLM 단독 근거 아님)
- **external_briefing_ref:** `athena_memory_bank.md` (Gemini prior-year memo, briefing only)
- **external_briefing_ref_v2:** `athena_memory_bank_v2.md` (time-series partition + firewall)

## 운영 체크포인트 (자동, 1줄)

<!-- ATHENA_CHECKPOINT_V1_START -->
- **2026-05-05T07:21:27Z** — 소배치 정리 추가 실행: freeze 50건 이동(session 20260505T072109Z), verify_p0 재통과(297/297)
<!-- ATHENA_CHECKPOINT_V1_END -->
---

## 에이전트 반복 루틴 (질의 없이, Fact-Lock)

대외·배포 작업을 매 세션 묻지 않으려면 아래 **파일 경로·exit code**만 따른다. NotebookLM·채팅 요약 단독 근거 금지.

| 트리거 | 할 일 |
|--------|--------|
| 대외 카피·보안·IP | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` + `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` |
| **어느 도메인에 어떤 쇼룸·허브 CTA 문구** | `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` **§1.1**·**§1.1b** (표·CTA 초안); `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md` §4.1 — **jema-ai.com Next 카피 원천(코드):** `projects/no1kmedi/marketing-site/public-copy.json` (`hub_links`; 공개 보드 권장 URL은 미니멀 HTML, `CONSTITUTION` Public Event Gateway 행 참조) |
| 공개 이벤트 스키마·지연 | `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`(bitcoin-trading `jemaai-cloud-mvp`) |
| 로컬 검증 번들 | `scripts/verify_p0_constitution_gate_paths.ps1` → exit 0; 필요 시 `scripts/run_jemaai_cloud_completion_chain.ps1 -SkipP1AB` |
| 원격 반영 | 지휘관 네트워크·리모트만: `scripts/push-internal.ps1`, 쇼룸 VPS는 `scripts/sync_showroom_to_vps.ps1`(의도·SSH 확인 후) — 에이전트는 **명시 요청 시에만** 실행·실패 로그 보고 |

---

## NotebookLM → 장기기억 체화 (한 파일 SSOT)

**가능하다.** 단, **에이전트가 장기기억으로 쓰는 것은 NotebookLM이 아니라 이 파일(및 Git)**이다. NotebookLM은 **참고·요약 원천**이고, 그대로 두면 세션·채팅마다 달라질 수 있으므로 **압축·검증 후 여기에만 반영**해야 **체화**된다.

| 단계 | 내용 |
|------|------|
| 1. 수집 | NotebookLM에서 노트·요약·소스 인용문 확보 (선택). |
| 2. 검증 | **구현·경로·수치**는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트와 대조. **불일치면 본 파일에 넣지 않음.** |
| 3. 압축 | 아래 **「NL 이관 압축」** 또는 **분기별 한 줄**에만 **고효율 한 줄**로 기입. 장문 붙여넣기 금지. |
| 4. 고정 | 커밋으로 버전 고정 → 모든 채팅이 동일 **중앙 메모리**를 읽음. |
| 5. 답변 | 에이전트는 **이 파일의 지문·표**를 우선하고, NotebookLM 내용은 **이미 이관·검증된 것**으로만 취급. |

**금지:** NotebookLM 출력만 보고 “구현됨/통과”라고 **이 파일에 적지 않는다.**

---

## VPS · 비트코인 본선 (혼동 방지 — 크로스 채팅 고정)

> **목적:** 런북·예시 파일의 **플레이스홀더 이름**과, 특정 호스트에서 **실측으로 확인된 PM2 앱 이름**이 다르다. 에이전트는 **아래 표 + 대상 호스트의 `pm2 list`** 를 우선한다. 구현 경로·게이트는 여전히 `CONSTITUTION_*`·스크립트가 우선(Fact-Lock).

| 항목 | 고정 (읽는 순서) |
|------|------------------|
| **원칙** | 문서의 `bitcoin-live` / 예시 ecosystem의 `mkm-btc-live` 는 **이름 후보·플레이스홀더**다. **재시작·배포 전에 대상 SSH 호스트에서 `pm2 list` / `pm2 show <name>` 으로 cwd·스크립트를 확인**한다. |
| **SSH 호스트 (로컬 ship 스크립트 기본)** | `vps-mkmlife` — `scripts/deploy/ship_to_vps.ps1` 의 `-VpsHost` 기본값. |
| **devops-mcp 실측 호스트(2026-05-04)** | `148.230.97.246` (`root`) — `project-0-workspace-devops-mcp`의 `check_vps_health`·`execute_vps_command` 성공. `pm2 list/show`는 기본 timeout(60초)에서 지연될 수 있어 `timeout=180`로 호출. |
| **실전 런타임 경로 (2026-05-04 실측)** | PM2 `bitcoin-live-small-24h`의 `exec cwd`는 **`/opt/bitcoin-trading-live`**, `script path`는 **`/opt/bitcoin-trading-live/start_live_trading.py`**. 실전 반영 판단은 이 경로를 1순위로 본다. |
| **보조 모노레포 경로(자동화/준비)** | `/opt/mkm-lab-workspace-v2` — `ship_to_vps.ps1` 기본값(`-VpsRepoPath`)이지만, 현재 `bitcoin-live-small-24h`의 직접 실행 경로는 아님. |
| **PM2 앱 이름 (실측)** | **온라인 24h:** `bitcoin-live-small-24h` — 동일 호스트에서 `bitcoin-live` 앱은 없음. 이름 변경 가능성이 있으므로 항상 `pm2 list`/`pm2 show` 실측이 우선. |
| **트리 정합 (2026-05-04 실측)** | `/opt/bitcoin-trading-live`: `origin=git@github.com:mkmlab-hq/bitcoin-trading.git`, `branch=main`, `HEAD=a97f44e9`, 워킹트리 수정(`AGENTS.md`, `config/trading_config.yaml`) 존재. `/opt/mkm-lab-workspace-v2`: `hq/destiny` 리모트 공존, `branch=main`, `HEAD=8167fdbd`, `origin/main` 대비 ahead 상태. |
| **배포 스크립트 적용 범위** | `scripts/deploy/linux/verify_and_reload.sh`는 **호출한 repo-path**에만 적용된다. `mkm-lab-workspace-v2`에서 성공해도 실전 PM2가 `bitcoin-trading-live`를 보면 실전 코드에는 즉시 반영되지 않을 수 있다. |
| **표 「분기별 한 줄」와의 관계** | 2026-05-02 `destiny` 브랜치 맥락과 2026-05-04 실전 PM2 경로(`/opt/bitcoin-trading-live`)는 다른 트리다. 한 줄로 합쳐 해석하지 않는다. |

**에이전트 고정 (재발 방지 · SSH 호스트 재질문 금지):** 위 표에 **SSH 기본 호스트(`vps-mkmlife`)·PM2 후보(`bitcoin-live-small-24h` 등)**가 있는 한, 답변에서 사용자에게 **“SSH 호스트 이름을 알려주세요”**, **“다음 턴에 호스트만 주세요”**처럼 **기본 대상을 재요청하지 않는다.** 사용자가 **명시적으로 다른 호스트**를 쓴 요청이면 그때만 전환한다. 생존·주문 모드는 **로컬 Cursor가 추측하지 않고**, Fact-Lock 확인용 명령은 **기본 호스트 `vps-mkmlife` 기준**으로 초안을 제시한다(실행·출력은 SSH 측). 예: `ssh vps-mkmlife "pm2 list && pm2 show bitcoin-live-small-24h"` → `script path`·`exec cwd` 확인 후, 해당 `cwd`에서 `config/trading_config.yaml`(또는 런북이 지정한 설정 파일)의 **live / observe / dry** 류 플래그를 **파일 근거**로만 서술.

**한 줄 요약:** 배포는 **`main` + FF** 가 기본이고, PM2 이름은 **호스트마다 `pm2 list`가 최종**이다.

---

## 조건부 시그널 게이트 · Binance USDM (경로 SSOT)

| 목적 | 진입점 |
|------|--------|
| 웹훅 전용(레거시 호환) | `projects/bitcoin-trading/scripts/run_conditional_signal_webhook_v1.py` → 내부에서 `run_conditional_action_gate_v1.py --backend webhook` 선행 |
| 백엔드 선택 | 동 디렉터리 `run_conditional_action_gate_v1.py --backend webhook` 또는 **`--backend api`** |
| 실주문 | 게이트에서 실거래 허용 조건 충족 후 **`--backend api`**; 주문 실행 단계는 스크립트 도움말·런북대로 **`--live`**·(의도 시) **`--mainnet`**; **선행(선택):** `run_conditional_action_gate_v1.py`에 **`--human-approval-json`**(또는 env `MKM_TRADING_HUMAN_APPROVAL_JSON`)이면 `validate_trading_human_execution_approval_v1.py` 선호출(exit 7); 파일럿 메인넷 소액은 `Run-BinanceUsdmPilotSmoke.ps1`가 기본으로 `reports/trading_human_execution_approval_latest.json` 요구 |
| 파일럿 스모크 | **`scripts/Run-BinanceUsdmPilotSmoke.ps1`** — 기본 dry-only. 테스트넷 실체결: **`-LiveTestnet -AcknowledgeLiveTestnet -RiskJson <fact_safe>`**. **소액 메인넷 실전:** **`-LiveMainnetSmall -AcknowledgeLiveMainnetSmall -AcknowledgeIrreversibleLoss -RiskJson <실제 fact_safe>`** + `-Qty`가 **`-MaxMainnetQty`(기본 0.002)** 및 선택 **`MKM_PILOT_MAINNET_MAX_QTY`** 상한 이하; **테스트 픽스처 risk 금지** |
| 일일 단일 판정 | `scripts/build_trading_go_nogo_status_v1.py` → `docs/final/artifacts/trading_go_no_go_latest.json` (gate + human approval + risk를 한 파일 `GO/NO_GO`로 고정; 주문 호출 없음) |

상세 한 페이지: `docs/binance_usdm_signal_webhook_setup_checklist_v1.html`.

---

## B-track LLM 번들 · macro / news (관측 한 줄)

**Fact-Lock:** 일일 체인은 선행 `scripts/build_btrack_news_macro_lens_adapters_v1.py` → `news_independent_lens_latest.json` / `macro_independent_lens_latest.json` → `build_btrack_llm_input_bundle.py`가 `artifacts`에 탑재; `generate_btrack_hypothesis_prophecy_v1.py`는 번들에 비어 있지 않은 `news_independent_lens` / `macro_independent_lens`가 있으면 **`macro_available`/`news_available` true**. 오프라인·직전 산출 재사용: **`run_btrack_daily_hypothesis_chain.ps1 -SkipNewsMacroAdapter`**. **Naver OpenAPI(`fetch_naver_openapi_signals_v1.py`)는 체인 기본 생략**; 네트워크 호출은 **`-IncludeNaverOpenApiRefresh`**(`.env`의 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`·개발자센터 API 활성 전제). 루트 `.env`는 체인 시작 시 Process로 로드(UTF-8 BOM·UTF-16 LE·`export ` 접두사 허용). 상세·회귀 경로·**일일 체인 전 스위치 표**는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 「일일 B-Track 번들」절 및 **바로 아래 `run_btrack_daily_hypothesis_chain.ps1` 스위치 표**. **복기 조립(가설+채점+선택 eval):** `scripts/eval_btrack_prophecy_post_mortem_v1.py` → `docs/final/artifacts/btrack_post_mortem_latest.json`; 주간 게이트 재점검 산출은 `docs/final/artifacts/trackb_weekly_gate_recheck_latest.json`.

---

## 로컬 워크스페이스 · 새 클론 SOP (표준)

> **맥락:** 매일 갱신되는 운영 산출물은 Git에 두지 않을 수 있어, **새 클론만으로는 로컬 “중간 재료”가 비어 있을 수 있다.** 후단 빌더만 단독 실행하면 입력 부족으로 중단될 수 있음(Fact-Lock).

**표준 순서 (중복 스크립트 추가 없음):**

1. **근본 재료:** `.env`(및 `.env.example` 대조)·외부 연동 키·Vault/네트워크 등 **스크립트 바깥 전제**를 먼저 갖춘다.
2. **최초 1회 풀 체인:** 별도 “부팅 전용” 래퍼를 만들지 않고, 이미 검증된 일일 러너 **`scripts/Invoke-MkmAiV2DailyReadiness.ps1`** 를 한 번 실행해 readiness·승격 포인터·Track C 패키지 연쇄·대시보드·가드까지 **순서대로** 로컬 산출물을 채운다.

**금지(운영 비대화):** 동일 목적의 두 번째 원클릭 부팅 스크립트를 레포에 추가해 관리 부담만 늘리지 않는다.

---

## 외부 브리핑 참조 (Athena Memory Bank)

- `athena_memory_bank.md`는 도메인/페르소나 정렬용 **브리핑 참조**로 사용한다.
- 과거 가설/확정 분리가 필요한 경우 `athena_memory_bank_v2.md`를 우선 사용한다(시계열 방화벽).
- 용어 교정(사심신물, 12 vs 8 체질, 자통)과 톤/협업 스탠스는 작업 중 우선 반영한다.
- 의료/디지털헬스/복잡계 맥락은 아이디어·설계 보조로 활용하되, 구현 완료 단정 근거로 쓰지 않는다.
- 구현·경로·성능·타임라인 확정은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트·아티팩트가 우선이다.

### 시계열 방화벽 (Time-Series Firewall)

1. `[DEPRECATED]` 태그 항목은 코드/설계에 재도입하지 않는다.
2. `[BRIEFING_ONLY]` 태그 항목은 아이디어·문맥 보조로만 사용한다.
3. 구현·경로·성능·타임라인 주장은 `CONSTITUTION_*`·exit code·artifact로 재검증 후 반영한다.
4. 충돌 시 레포 SSOT가 항상 우선한다.

---

## NL 이관 압축 (검증 후만 · 최대 10줄)

> 아래는 **NotebookLM 소스 브리핑**을 교차 질의해 압축한 것. **구현·수치·경로는** 항상 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트로 재확인. 충돌 시 레포 SSOT 우선.

1. 투트랙: A(상용·범용)·B(리터럴·연구) **물리 격벽** — B→A 자동 합선·실매매 자동 트리거 **금지**가 소스 전반 반복 테마.
2. Fact-Lock: 판정은 **디스크·호출 가능 스크립트·exit code**; 브리핑·NL 수치는 **FACT/HYPO 분리**·단정 금지가 반복됨.
3. 레짐: **1차 실물·시장** vs **2차 성경·명리** 보조; 2차를 실전 트리거에 쓰지 않는 **주·보** 구분이 Fusion/Ops 소스와 정렬.
4. 멀티렌스: 로고스·명리·사상 **격벽** 유지, 단일 TOE·통일장 **완성 선언 금지** — NL·문서 관점 일치.
5. 예언 레일: 일반예언은 **루트 스키마·게이트** SSOT; 로고스 예언 파이프라인과 실물·실매매 엔진 **동일 프롬프트 혼재 금지** 브리핑.
6. 압축·품질: Jaccard·무결성·절감 등은 **재현 산출물**로만 강하게 주장; 브리핑 수치는 **검증 전 제한** — 압축 노트 요지.
7. 배포: 로컬·Sandbox·VPS **역할 분리**; jemaai 공개 쇼룸 vs 본선·조종실 **지연·권한 격리** — Ops 브리핑.
8. 단일 진입·게이트: `evaluate_report`·P1·직렬 pytest 등 **품질 게이트** 언급은 MKM_CORE 브리핑 — **실제 경로는 Fact 표 대조**.
9. 12AI·운영: 지휘·자동화는 **게이트·라벨**(FACT/HYPO/STRAT) 중심 서술이 많음 — **구현 여부는 코드만**.
10. **범위:** 위 요약은 **NL에 올라온 2026년 초~중순 자료** 기준; “작년 한 해” 전체가 아니면 **추가 소스 업로드 후 재동기화** 필요.

### Logos 원어 스택 — 세션 간 혼동 방지 (Fact-Lock)

1. **마스터 아톰** (`scripts/core/build_original_language_master_atoms.py`): 입력은 `verse_decoded_v2.jsonl`+외경+DSS; 고유형 ~4.2만·헬라 ~1.4만은 **요약 JSON**의 `unique_*` — **정규화·가벼운 휴리스틱**이며 완전 형태소 분석 아님 (`original_language_master_atoms_summary_*.json`·스크립트 note).
2. **레짐 특이점 리포트** (`scripts/core/build_original_corpus_regime_singularity_report_v1.py`): 구절→`build_gematria_metadata`→`build_gematria_4d_bridge`→레짐 지문과 **내적 스코어**; 물리적 에너지 아님·산출 `hypothesis_tier:B`.
3. **코퍼스 분리**: 두 파이프라인은 **동일 산출물이 아님**. 특이점 기본 인자는 DSS/외경 JSONL; 정경 전체를 쓰려면 **`--canon-jsonl`**로 `verse_decoded_v2.jsonl` 등을 넣고 레인 **`canon`**으로 분리(동일 스크립트에 2026-04-23 패치).

---

## 이론 고효율 압축 — Athena 정체성 지문 (맥락 복원용)

> 아래는 **레포 헌법·AGENTS·Fact-Lock**에서 뽑은 **지문만** 압축한 것이다. 장문·내러티브 금지. 상세는 항상 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 등 SSOT.

| 지문 | 한 줄 |
|------|--------|
| 3+1 | 파이프라인 층: **Seed·Label·Formula·Field** — 만물이론·단일 방정식 완성 **아님** (Fact-Lock). |
| 4D Seed | 순수 뼈대 `[S,L,K,M]` — 코드 4D와 Prism 논리 색인 혼동 금지. |
| Field | **“지금이 어떤 판인가?”** — 레짐은 역사 고유명(IMF·리먼·IT버블·코로나 등), 안정/주의/위험만으로 끝내지 않음. |
| 레짐 주·보 | **1차** `regime_map` 실물 **주** · **2차** 성경 매트릭스 **보** — 2차는 해설·리포트, **실전 트리거 금지**. |
| Multi-Lens | 로고스·명리·외경 등 **격벽** — 단일 TOE·통일장 완성 선언 금지. |
| Fact-Lock | 구현 여부·경로는 **디스크 + 호출 가능 `.py`/`exit code`** — NotebookLM·브리핑 단독 근거 금지. |
| 예언 레일 | B 레일 일반예언은 **루트 스키마/스크립트 SSOT** — 서브트리 이중 복제 금지. |
| 멀티레인 | 성경·명리·사상 **각각** 기준 통과 후 퓨전 — 한 레인 실패를 타 레인으로 메우지 않음. |
| 압축 트랙 | Track A 범용 / Track B 리터럴 — 격벽·상용 게이트는 `P0`·SLA 정책 선. |
| TITAN | Command-by-negation — 저위험은 합리적 기본값·사후 보고; 고위험만 승인. |
| 정체성 답변 규칙 | 전략·답변·코드 모두 **위 지문과 충돌 시 지문·SSOT 우선** — “그럴듯한 확장” 금지. |
| 에이전트 연속성 | **In-Turn:** 한 요청 안 다단계(토큰·시간·정책 상한). **Ops:** `scripts`·스케줄·exit code — 채팅 세션과 동일시 금지. **≠** 사람 새 입력 없는 무한 채팅 루프. 맥락 복구는 **이 파일·Git** + 「작업 맥락 레슨」(약 328-334행). |

---

## MKM AI 고도화 · 자체 LLM (의사결정 지문)

> 지휘관 질의: “규칙 주입 vs 가중치에 이론 체화”, “로컬 젬마4 등을 MKM 사고로 내장할지”. **구현 완료 단정은 Fact 표·스크립트로만** — 여기는 **전략 지문**만.

1. **층 분리:** Cursor 규칙·시스템 프롬프트 = **런타임 정렬(가중치 불변)**; 파인튜닝·어댑터 = **선험(prior) 변경**. 둘 다 “주입”이지만 **다른 레버**다.
2. **기본안(대부분 충분):** 규칙 + RAG + **게이트·eval·스키마**로 행동 고정. Fact-Lock·투트랙·레짐 주·보는 **프로덕트에 새기기 전에** 여기서 먼저 고정.
3. **자체 LLM/체화는 조건부:** 반복 출력 형식·금지 패턴·브랜드 톤이 **데이터·자동 채점**으로 정의되고, **규칙만으로 프롬프트가 비대**해 비용·일관성 문제가 **실측**될 때만 — 어댑터·좁은 파인튜닝을 **ROI 검토** (데이터 파이프라인·회귀 없으면 **오버엔지니어링**).
4. **속도:** 느림의 주원인은 “규칙” 자체가 아니라 **토큰 길이·호출 구조**; 학습으로 프롬프트를 줄이면 이득 볼 수 있으나 **학습 성공·평가 전제** 필요.
5. **재질의 시 응답:** 동일 주제 재질의 시 **본 절 + Fact 표**를 우선 인용해 답을 맞추고, NotebookLM·세션 감으로만 재정의하지 않음.

---

## 명리 렌즈 고도화 v1 (MKM 표준 · 삼고 · 만세력)

> **목적:** 명리를 **중기 방향 코어**로 두되, 만세력·수학화·MKM AI는 **재현 가능한 산출물·스키마**로만 말한다. 날씨·일반예언 체인에서 온 통찰은 **캘리브레이션·홀드아웃·게이트·FACT/HYPO 분리** 같은 **운영 원리만** 차용하고, **명리 결정론 엔진과 데이터 자동 합선 금지** (§1.1 격벽·B→A 금지와 동일 방향).

### 답변·산출 규약

- **순서:** `Field(레짐)` → `Lens(사상/명리/성경)` → `Conflict` → `Final Action`; 성경은 `[NON_GATING]`, 최종 액션은 **1차 실물 레짐 + 운영 게이트**.
- **명리가 말하는 것:** 대운·월령·지장간·4D 블렌드 등 **구조·타이밍·중기 방향** 서사. **말하지 않는 것:** 실매매·임상·단일 운명 단정·TOE/통일장 완성 주장.

### 만세력 정확도 (Fact-Lock)

- **입력 1순위:** `birth_instant_utc`(ISO Z) + **IANA TZ** — `AGENTS.md` 만세력 절·`docs/final/artifacts/schemas/saju_global_birth_request_v1.schema.json` 계약과 정렬.
- **엔진 검증:** `scripts/run_manseryeok_validation_smoke_v1.py`(코호트·충돌 사전 등); 회귀 기준은 **`pillars_native`**; 외부 UI 스냅샷은 **`pillars_external`**로 분리 표기.
- **MCP 기본 경로:** 만세력 MCP는 **`athena-manseryeok`** 단일 기본(2026-04-30 CENTRAL 잠금과 정합); 상세 표는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§3.3·§3.4** 및 만세력 관련 행.

### MKM 명리 표준 스택 (구현 SSOT)

- **4D 융합 결정론:** `scripts/myeongri_complete_fusion.py` (`MyeongriCompleteFusion`), `scripts/run_manseryeok_bot_v1.py` (`analysis_depth=pro` 시 fusion·대운·起運·`vector_4d_rule_school_v1` 등); 지장간 LUT/가중·대운·`rule_school_mkm_4d_v1`·회귀 경로는 **`CONSTITUTION` §3.3 표**가 단일 색인.
- **독립 렌즈 v0/v1:** `scripts/run_lens_myeongni.py` + 계약 JSON·스키마; 봇→융합→렌즈 원클릭 `scripts/run_myeongni_lens_chain_from_bot_v1.py` / `scripts/Run-MyeongniLensChainFromBot_v1.ps1`.
- **LLM은 보조 해석만:** `docs/final/MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md` + `docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json` + `scripts/run_myeongri_ai_interpretation_pack_v1.py` — **결정론 JSON 위 NL 봉투**; 쟁점·실전 최종 판정 금지.
- **대외 서술 어휘:** `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md` (코드 식별자·스키마 키는 변경하지 않음).

### 삼고 수학화 (입력·엔진·출력 삼중 고정)

1. **고입력(考入力):** 요청 본문을 **스키마·타임존**으로 정규화; `scripts/saju_birth_resolver_v1.py` / `scripts/run_saju_global_birth_v1.py`와 동일 계약 유지; DST 모호 구간은 **추측 보간 금지**·에러 또는 명시 확인.
2. **고엔진(考引擎):** 만세력 스모크·`tests/test_myeongri_*`·지장간·대운·起運 회귀; dual-regime·트레이딩 그래프 쪽은 **`source_track: B`**·ledger 접두 등 **명리 네임스페이스 격벽** (`CONSTITUTION` §3.1·§3 전반).
3. **고출력(考出力):** `myeongni_independent_lens_v1` 등 **스키마 검증된 JSON**만 SSOT; 재현 해시가 있는 CLI는 §3.3의 `--deterministic-json` / `--hash-deterministic-json` 경로를 우선.

### 날씨·일반예언 레일에서 빌린 통찰 (원리만)

- **차용:** 라벨→`general_prophecy` 트리플·Brier·ECE·홀드아웃 — 루트 **`GENERAL_PROPHECY_SCHEMA_V1`** 및 `AGENTS.md` 「일반 예언(B 레일)」절의 스크립트 체인 (`scripts/run_weather_gt_to_prophecy_triplet_chain_v1.py` 등).
- **금지:** 날씨·가격 예언 JSON을 만세력/명리 4D **결정론 파이프라인에 자동 병합**; uplift·적중 주장은 **해당 eval 산출물** 없이 명리 해석에 끌어오지 않음.

### MKM AI (4AI 코어 + Absolute Balance Coordinator Mode)

- **층 분리:** 상위 절 「MKM AI 고도화 · 자체 LLM」과 동일 — 규칙·게이트·스키마가 **행동 고정**; 파인튜닝·어댑터는 **별 ROI·eval 전제**.
- **혼동 방지:** `mkm_ai_status_pointer_latest.json` 등 **운영 승격 스택**은 인프라·게이트 준비도이며, **명리 예측력·만세력 정확도 증명으로 읽지 않음**.
- **인덱스·P0:** `MKM_TRINITY_INDEX_V1.json`의 `lenses.myeongni.validation_pointers`에 본 파일(`docs/final/CENTRAL_AGENT_MEMORY_V1.md`) 포함; `verify_p0_constitution_gate_paths.ps1`이 동 파일 **존재**를 검사; `tests/test_mkm_trinity_index_v1.py`가 포인터 경로 **파일 존재**를 회귀 고정.

---

## 분기별 한 줄 (최근 1년 · 수동 채움)

> 팀이 실제로 한 **결정·이정표**만 적는다. 비우면 됨.

| 기간 | 핵심 한 줄 (무엇을 확정/중단/승격했는지) |
|------|----------------------------------------|
| 2026-Q1 (NL 코퍼스) | NotebookLM MKM·Ops·Fusion 등 15노트 교차 질의 → 본 파일 **NL 이관 압축** 반영 (레포 SSOT와 병용). |
| 2026-Q2 (AutoEvo) | 조사→큐→스캐폴드→실행→제안→승인→결정 적용 + 연구 레인 승격 실행계획(`autoevo_research_promotion_plan_latest.json`) 생성. |
| 2026-Q2 (Hybrid Pointer Router) | `GO/WATCH/HOLD` 라벨링·runtime config·shadow 리포트·alert·guard·강등 드릴까지 연결해 “조건부 고효율 + 자동 하방보호”를 아티팩트 체인으로 고정(무조건 99/100 수사 금지). |
| 2026-05 (MKM 렌즈·융합 점검 루프) | 명리·사상·로고스 독립 렌즈·통찰 번들·융합 스텁·Shadow·신학 연동을 **pytest + P0**로 스모크; 통합은 `gitea/main`·`SoloDev-MergeFeatureToGiteaMain.ps1` 절차로 정리(관측/ B-track, A-track·실전 자동 합선 없음). |
| 2026-05-05 (Yang 2015 표면 8자 B-track) | `btrack_yang_2015_style_metrics_v1`·`run_myeongni_celebrity_benchmark_v1`·JSON Schema·`verify_p0`·`dual-regime`/`multilens`/`run_fact_lock_bundle` 회귀; 일일 체인은 **`-IncludeYang2015SurfaceMetrics`** 옵션으로만 갱신(기본 생략); 산출은 `.gitignore`로 재생성물 분리·**임상·A-track 자동 트리거 없음**. |
| 2026-05-05 (명리 결정론 코어 회귀) | `test_myeongni_independent_lens_v0`·`test_myeongni_lens_v1_contract`·`test_myeongni_fusion_bridge_v1`·`test_myeongni_lens_chain_from_bot_v1` **11 passed** + `verify_p0` 경로 정합; 모호한 자연어 단정보다 **스키마·pytest·P0**로 “선택 공리형” 지시를 배제하는 축 강화; PointerGuard **일일 태스크 Disabled**면 readiness `all_ok=false` 유지(운영 선택). |
| 2026-05-05 (jema-ai.com 허브 CTA 3분기) | `projects/no1kmedi/marketing-site/public-copy.json`의 `hub_links`에 `showroom_jemaai`·`premium_mkmlife`·`b2b_acodeai`를 코드 SSOT로 고정하고 히어로에 순서 렌더; `MKM_DOMAIN_PORTFOLIO_POINTER_V1` §1.1b·`TRACK_C_IP_BUSINESS_PLAN` §3.6 문서 동기화; `npm run check:marketing-copy`·`npm run build` 통과 후 레포 커밋. |
| 2026-05-05 (공개 쇼룸 권장안 = 미니멀 보드) | `public_showroom_board_minimal.html` 배포·scp·nginx·SPEC·`CONSTITUTION` Public Event/배포 행·P0 경로·autopilot jemaai 체크에 포함; 허브 `showroom_jemaai.href` → `api.jemaai.cloud/.../public_showroom_board_minimal.html`; `run_jemaai_cloud_completion_chain.ps1 -SkipP1AB` OK. |
| 2026-05-04 (MKM Trinity index v1) | 렌즈 키 `sasang`/`logos`/`myeongni` + `constitution_anchor` + `validation_pointers[]` + `_meta.schema/version`를 `MKM_TRINITY_INDEX_V1.json`에 박제; jsonschema·`dual-regime-integrity`·`run_fact_lock_bundle`·`verify_p0`에 연결(목차만, FACT는 헌법·스크립트). |
| 2026-Q1 (레포 타임라인) | Mar~Apr `feat`/`docs`/`chore` 커밋이 다수 + `reports`·`docs`·`scripts` 경로 변경이 두드러짐 → **산출·스냅샷·자동화**를 한 사이클로 밀어붙인 분기 (`docs/final/artifacts/memory_revival_gap_scan_latest.json`와 대조). |
| 2025-05~2026-02 (갭·NL 검증) | NotebookLM `압축` 노트(`c5f9aef1-6cd6-4c3b-9c57-d1f2a62e3201`) 교차질의가 인용한 source id는 **현재 `nlm source list` 제목**(예: 2026-04-09 H: 매니페스트·`top10_curated`)과 시점이 맞지 않음 → **날짜별 “결정 연대기”는 미승격**; 동 구간 본 레포 `git log` **0건** 재확인. |
| 2026-04 (Cursor · 크로스 채팅) | `.cursor/rules/central-agent-memory.mdc`에 **SSOT 핵심 5줄**(Fact-Lock·투트랙·레짐 주·보·Multi-Lens·압축 서술)을 **매 턴 자동 포함**으로 고정; 압축 대외 서사는 **실행층=휴리스틱·게마/4D 브리지=계측·사원수=trackb 실험축**으로 Fact-Lock 정렬. 채팅 간 맥락 누적은 **본 파일·Git** — 세션 로그 자동 병합 아님. |
| 2026-04 (국방 제안 브리핑 · 검증 가능 주장만) | **합성 UAV 하이브리드 벤치** `run_defense_hybrid_compression_bench.py`→`defense_hybrid_compression_bench_v0.json`: `critical_field_integrity=1.0`, `mean_payload_compression_ratio≈25.46%`, `research_only`; 크리티컬 경로는 msgpack 무손실·시맨틱 레인은 literal Track B·**라우터/코드북/게마트리아 비활성**. 대외: 타사 좌표오차 비교·「4D=암호」·스푸핑 차단 단정 금지 — `ATHENA_AUDITOR_REALITY_ALIGNED_EXTERNAL_V1_2026-04-09.md`·아티팩트 note 정합. |
| 2026-04-19 (B-track insight + LG 골든 + Vault) | **Vault:** `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` 성공(복사 50). **레포(Fact-Lock·경로):** B-track 캘린더 스텁 JSONL·렌즈/사이드카 기본 경로 정합, `Run-BtrackInsightSidecarChain`에 overlay(`btrack_prophecy_score_insight_overlay_view_v1`)·`register_btrack_insight_sidecar_chain_task.ps1`, P0 게이트 경로 확장(~129), Prism/인벤토리/프로모션 브리지 갱신; LG 워셔 골든 `validate`+CI+P0+브리지 `lg_washer_voice_golden`, 관련 스크립트 `ROOT` repo-relative; 예언 dual refresh·live_ab·defense_edge·`docs/verified_knowledge_base/update_all.py`·codepack step2·`crypto_nitro_live_strategy`/`auto_evolution_engine`의 `C:/workspace` 제거(환경변수 폴백). **승격·walkforward 게이트 입력은 기존 점수 JSON만** — overlay는 관측용. |
| 2026-04-19 (A-track go/nogo + getenv) | `python scripts/build_a_track_go_nogo_status.py --on-system-error hold_s1`로 `docs/final/artifacts/a_track_go_nogo_status_latest.json` 재생성: 로컬에 `data/chronos_forward_training/holdout_2026_result.json` 있으면 `input_errors` 비움·방향일치율 스냅샷 반영; **S2는** `prophecy_2026_monthly_kospi_btc_fact_safe_v1.json` meta의 `high_reliability_decision=HOLD`·`price_output_locked=true` 및 S3/S4 플레이스홀더로 계속 HOLD/S1. `build_manseryeok_database_from_sajupy_advanced.py`·`trading_wisdom_loader.py`·`build_standard_codebook.py`에서 `os.getenv(...,"C:/workspace")` 제거( repo-relative 또는 `WORKSPACE_ROOT`만). **`/data/`는 gitignore** — 클론만으로 chronos JSON은 없을 수 있음. |
| 2026-04-19 (LG 게이트·경로·Phase3 검증) | `check_lg_washer_measurement_gate_v1`·`check_lg_washer_estimation_readiness_v1`·`build_btrack_promotion_signoff_packet_v1` 재실행(측정은 여전히 proxy·실측 교체는 장비 수령 후). `bitcoin-trading` `src`/`ops`·`biblical_single_lane_trading_hook`에서 `C:/workspace` 리터럴 제거; `strategic_failure_event`/`strategic_news_extractor` 워크스페이스 `memory` 경로를 `parents[4]`로 정정. `pytest` `test_btrack_phase3_snapshot_sync`·`test_btrack_prophecy_score_insight_sidecar_stub_v1` 통과. |
| 2026-04-19 (대기열 PS) | `run_waiting_queue_btc_binance_daily.ps1`의 고정 `C:\\workspace` 제거·`PSScriptRoot`에서 레포 루트 4단계 상위로 해석; CENTRAL `다음에 할 일`을 실측·푸시·P0/대기열 점검 축으로 재작성. |
| 2026-04-20 (멀티렌즈 회귀) | `pytest`: `test_independent_lenses_v0`·`test_independent_lens_shadow_gate_v1`·`test_independent_lens_fusion_stub_v0`·`test_scm_boming_jiju_lexicon_v1`·`test_eval_btrack_insight_sidecar_lens_hit_agreement_v1` 일괄 **13 passed** — 명리/사상/로고스 렌즈 러너·섀도 게이트·퓨전 스텁·보명지주 렉시콘·사이드카 렌즈 일치 eval이 CI 가능 상태로 유지됨을 확인. |
| 2026-04-20 (멀티렌즈 CI) | `.github/workflows/multilens-independent-lens-smoke.yml` 추가: 위 pytest 번들을 path-filtered push/PR에서 자동 실행; `verify_p0_constitution_gate_paths.ps1`·`MKM12_PRISM_INDEX_REGISTRY_V1.json`에 워크플로 경로 등록. |
| 2026-04-20 (메모리 큐) | `다음에 할 일` 갱신: 푸시 완료 항목 제거 → **CI 녹색 확인**·**미커밋 artifact 정리/의도 커밋**·LG 실측 대기 유지. |
| 2026-04-20 (Bio Sasang n-state strict) | FireProtDB DDG strict 코호트(4,783)로 `n_states=8/10/12/14` 대칭 비교(family 5-fold·seeds 42/43/44·bootstrap 5000): Spearman 순위 **12(0.5295) > 14(0.5175) > 10(0.5028) > 8(0.4958)**. 현 벤치마크 최적 상태수는 **12**로 고정 (`reports/bio_sasang_nstates_strict_comparison_v2.json`). |
| 2026-04-20 (NotebookLM insight action sync) | 노트북 `dna와사상`에 `Action Plan: Sasang x DNA next experiments`를 저장하고, 실행 우선순위를 `SNP x constitution` 상호작용 AB → 12상 외부 강건성 → multimodal 강건성으로 고정. 분자 비유 레이어(토토머/금속매개 안정화)는 운영 주장으로 승격하지 않고 `research_only`를 유지. |
| 2026-04-22 (Multitarget strict HOLD + trainability gate) | scaffold/target-holdout 재벤치 및 runtime policy 리허설 이후 `generalization_gate_decision_strict_hold_latest.json`이 `HOLD` 고정; 추가로 target-conditioned PoC와 `target_conditioned_trainability_gate_latest.json` 실행 결과, `stage2_trained_target_count=0`·`topology_trainable_target_count=0`으로 연구 게이트도 `HOLD` 확정. |
| 2026-04-22 (B-track dual-lane autogate v4 pass) | `evaluate_b_track_staged_go_nogo_v4.py`로 AUROC 단일클래스 미정의를 `WARN-DATA-003`로 분리하고, `run_ab_track_autogate_pipeline_v3.py --rebuild-unseen-split --unseen-heldout-target EGFR --rebuild-seen-label-split --b-gate-evaluator v4 --allow-auroc-missing-single-class-test` 재실행 결과 `artifacts/weekly_status_v3.json`에서 `a_pass=true`, `b_unseen_pass=true`, `b_seen_label_pass=true`, `all_pass=true` 달성. |
| 2026-04-23 (Logos 파이프라인 혼동 방지 + canon 레인) | 마스터 아톰 집계 vs 레짐 특이점 리포트는 **서로 다른 입력·목적** — Fact-Lock으로 구분해 `CENTRAL_AGENT_MEMORY`에 고정. 특이점 스크립트에 **`--canon-jsonl`**·레인 `canon` 추가; Vault 미러 스크립트에 **`MKM_OBSIDIAN_VAULT_ROOT`**·기본 `memory/obsidian_vault` 스텁; 글로스 v4 보수 접두 체인은 코드북·HYPO 보조 유지. |
| 2026-04-28 (성경×우리이론 융합 게이트 완성) | Multi-symbol(선악과/바벨/출애굽) 공진·4D·survivability·drift·negative/counterfactual·통합 게이트(`multi_symbol_gate_summary_latest.json=GO`)와 Q&A 동적 근거 주입까지 E2E 체인+pytest로 잠금. |
| 2026-04-28 (PointerGuard 상용 게이트 고정) | 폴더 정책 allow/caution/forbid + shadow alert/guard + memory_v2 ramp/freeze + 운영 스모크 + 일일 스케줄러 + Tier2 서비스형 부하(`max_error_rate=0`, worst `p95=159.50ms`, worst `p99=171.77ms`)까지 연결. 대외 판정은 **`GO_FOR_CONTROLLED_B2B`**, 글로벌 초대형 주장(`global-scale`)은 **Tier2 host 리소스 계측 보강 전 보류**. |
| 2026-04-29 (Global Atom 수치 락 복구) | `3051269 edges`(약 305만) 근거를 freeze onepager(`.../freeze/global_atom_submission_20260428T095850Z/global_atom_network_academic_onepager_latest.json`)로 재매핑하고, `global_atom_claim_lock_registry_latest.json` + `check_global_atom_claim_lock_v1.py`로 주장-근거-해시 재검증 루프를 고정. |
| 2026-04-29 (A-track go/nogo 의미 분리 복구) | `build_a_track_go_nogo_status.py`의 의미 충돌(`snapshot: HOLD/lock` vs `checks: not_hold/unlocked=true`)을 수정해 runtime 상태 체크(`high_reliability_decision_not_hold`, `price_output_unlocked`)와 정책 준비 체크(`high_reliability_release_plan_defined`, `price_unlock_policy_defined`)를 분리; pytest 통과 후 재생성 결과를 `HOLD/S1_SHADOW`로 일치시킴. |
| 2026-04-29 (31.71 융합·재검증 고정) | `check_role_router_shadow_forward_validation_v1.py`를 재검증 스위트에 융합하고 `required_oos_days=252`·`min_hit_rate_active=0.52845(BTC)`·`--promotion-gate-json`(gate-pass 우선)을 반영해 `GO_LIVE_CANDIDATE` 수신증명은 유지하되, `logos_directional_viable_under_current_setup=false`와 의미를 분리 고정. |
| 2026-04-30 (외부 성경 앵커 governance + CI 스모크) | **브랜치:** `origin/fix/external-anchor-ci-smoke`(스모크 deps 커밋 `d5bc42c965` 포함)·Dual Regime 워크플로에 `tests/test_external_anchor_governance_scripts_smoke_v1.py` 등록. **혼동 방지:** PR/CI와 동일 트리 작업은 전용 **git worktree** `C:\workspace\tmp\wt-external-anchor-work`를 쓰고, 메인 `C:\workspace`는 `fix/open-bench-c3c5-gates`·대량 로컬 수정·`.git/info/exclude`의 `scripts/*` 영향으로 원격과 다를 수 있음 — 앵커 스크립트·주간 순서(sustain→sync→append→sustain→sync→overwrite)·`adopt_limited_strict` 스트릭은 스모크·`run_layer1_layer5_weekly_maintenance_v1.ps1`로 Fact-Lock. |
| 2026-04-30 (투고 패킷·운영 게이트 잠금) | 대외 문구 가드(`build_external_message_claim_guard_report_v1.py`)를 CI·주간 러너에 고정하고 Dev/Prod 스케줄을 분리(Prod claim_guard ON); 제출 패킷(`mkm_submission_packet_v1` + camera-ready/caption/rebuttal + preflight) 완성 후 핵심 5개 evidence와 claim guard를 T-1/T-0 시점으로 재생성해 `status=pass`·최신 `generated_at_utc`를 잠금. |
| 2026-04-30 (MCP 혼동 방지 표준화) | Cursor MCP 운영을 단순화: 만세력은 `athena-manseryeok` 단일 기본(기존 `manseryeok-mcp` 비활성), 브라우저는 `openchrome` 기본(중복 `playwright` 비활성)으로 고정해 도구 선택 혼동을 예방. 추가로 기본 메모리 서버를 `@modelcontextprotocol/server-memory`에서 `athena-core(MKM12_LTM_DB_TYPE=file)`로 교체해 장기기억 일관성을 강화. SSOT 반영 경로는 `C:/workspace/.cursor/mcp.json`. |
| 2026-04-30 (NotebookLM 동기화 재확인) | `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` 수동 실행 `exit 0`; Vault 마커 `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\_LAST_SYNC.txt` 기준 `UTC 2026-04-30T13:42:31Z`, `copied=103`, `skipped=92` 확인. 정책상 cloud ingest(`source_add`)는 별도 단계로 유지. |
| 2026-04-30 (MKM AI v2 승격 게이트 자동화) | 승격 체크리스트 `docs/final/MKM_AI_V2_FINAL_PROMOTION_CHECKLIST.md` 추가 + 자동 점검 `scripts/run_mkm_ai_v2_readiness_check.ps1` 신설. 실행 결과 `docs/final/artifacts/mkm_ai_v2_readiness_latest.json` `overall_passed=true` 확인(코어 MCP 8개 일치, 금지 서버 부재, `athena-core` LTM=file, NotebookLM sync marker fresh). |
| 2026-04-30 (헬스체인 통합) | `scripts/run_workspace_automation_health.ps1`에 `-IncludeMkmAiV2Readiness` 옵션을 추가해 v2 승격 게이트를 운영 헬스체인에 연결. 스모크 실행(`-SkipVaultMirror -SkipMkmMemoryInventory -SkipPhase1Readiness -SkipNewsObservationContractSmoke -IncludeMkmAiV2Readiness`)에서 `MKM AI v2 readiness gate: OVERALL PASS` 확인. |
| 2026-04-30 (일일 자동운영 연결) | 러너 `scripts/Invoke-MkmAiV2DailyReadiness.ps1` 및 등록기 `scripts/Register-MkmAiV2ReadinessDailyTask.ps1` 추가. 태스크 `MKM_AIV2_DailyReadiness` 등록(`State=Ready`) 및 로그 `reports/mkm_ai_v2_readiness_log.jsonl` append 확인. |
| 2026-04-30 (주간 합격률 리포트 자동화) | `scripts/build_mkm_ai_v2_weekly_readiness_report.py` 추가 후 일일 러너에서 자동 호출하도록 연결. 산출 `docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json` 생성 확인(`pass_rate_percent=100.0`, `sample_count=1`, 7일 윈도우). |
| 2026-04-30 (최종 승격 판정기 추가) | `scripts/check_mkm_ai_v2_promotion_decision.py` 추가(기본 임계: `pass_rate>=95`, `sample_count>=3`) 및 일일 러너 연동. 산출 `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`에서 현재 `decision=HOLD_OPERATIONAL_V1`(readiness PASS, 표본수 2로 최소 표본 미달) 확인. |
| 2026-04-30 (v2 최종 승격 조건 충족) | 일일 러너 추가 실행으로 `reports/mkm_ai_v2_readiness_log.jsonl` 7일 표본이 `sample_count=3`에 도달. 최신 판정 `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`에서 `decision=GO_FINAL_V2`, `promotion_ready=true`, `pass_rate_percent=100.0` 확인. |
| 2026-04-30 (v2 Final 승격 잠금) | 승격 잠금 아티팩트 `docs/final/artifacts/mkm_ai_v2_final_promotion_lock_latest.json` 생성(`status=APPROVED_FINAL_V2`, `system_label=MKM AI v2.0 (Final)`). 운영 명칭을 `MKM AI v2.0 (Final)`로 승격. |
| 2026-04-30 (승격 잠금 자동 동기화) | `scripts/sync_mkm_ai_v2_promotion_lock.py` 추가 후 일일 러너에 연동해 판정 결과(`GO/HOLD`)에 따라 잠금 상태를 자동 갱신하도록 고정. 최신 잠금 `schema=v2`, `status=APPROVED_FINAL_V2`, `weekly_sample_count=4` 확인. |
| 2026-04-30 (단일 상태 포인터 추가) | `scripts/build_mkm_ai_status_pointer.py` 추가 후 일일 러너에 연동. 산출 `docs/final/artifacts/mkm_ai_status_pointer_latest.json`에서 `status=APPROVED_FINAL_V2`, `system_label=MKM AI v2.0 (Final)`, `is_final=true`를 단일 참조로 제공. |
| 2026-04-30 (상태 브리프 자동화) | `scripts/build_mkm_ai_status_brief.py` 추가 후 일일 러너에 연동해 사람이 읽는 요약 `docs/final/artifacts/mkm_ai_status_brief_latest.md` 자동 생성. 최신 값 `status=APPROVED_FINAL_V2`, `weekly_sample_count=6` 확인. |
| 2026-04-30 (Final Ops Bundle 추가) | `scripts/build_mkm_ai_final_ops_bundle.py` 추가 후 일일 러너에 연동. 통합 산출 `docs/final/artifacts/mkm_ai_final_ops_bundle_latest.json/.md`에서 Final 상태·주간 합격률·NotebookLM sync marker를 한 번에 확인 가능하도록 고정. |
| 2026-04-30 (Final Ops Guard 고정) | `scripts/check_mkm_ai_final_ops_guard.py` 추가 후 `run_workspace_automation_health.ps1`에 `-IncludeMkmAiFinalOpsGuard` 옵션 연결. 스모크 실행에서 `FINAL OPS GUARD: PASS` 확인(`status=APPROVED_FINAL_V2`, `decision=GO_FINAL_V2`, `sample_count=8`). |
| 2026-04-30 (Final Guard 일일 스케줄링) | `scripts/Invoke-MkmAiFinalOpsGuard.ps1` + `scripts/Register-MkmAiFinalOpsGuardDailyTask.ps1` 추가. 태스크 `MKM_AIV2_FinalOpsGuard_Daily` 등록(`State=Ready`) 및 로그 `reports/mkm_ai_final_ops_guard_log.jsonl` append 확인. |
| 2026-04-30 (`.cursorrules` 강제 SSOT 고정) | 레거시 본문 재주입 이슈 대응: 템플릿 `docs/final/artifacts/cursorrules_slim_ssot_v1.txt` + 강제 적용기 `scripts/enforce_cursorrules_slim_ssot.py` 추가. 일일 러너 시작 단계에 enforcer 연동 후 `.cursorrules`를 2924 bytes 슬림 상태로 안정 유지 확인. |
| 2026-04-30 (지식 호출 스트레스 테스트) | `scripts/run_mkm_ai_knowledge_retrieval_stress_test.py` 추가/실행. 산출 `docs/final/artifacts/mkm_ai_knowledge_retrieval_stress_latest.json/.md`에서 `hit_rate_percent=100.0`, `avg_latency_ms=0.234`, `p95_latency_ms=0.334`, `passed=true` 확인(슬림 규칙 상태에서도 핵심 앵커 검색 성능 유지). |
| 2026-04-30 (Track C 상업화 패키지 생성) | `scripts/build_mkm_trackc_commercial_package.py` 추가/실행. 산출 `docs/final/artifacts/mkm_trackc_commercial_package_latest.json/.md` 생성(`macro_risk_api_smoke_present=true`, `macro_risk_policy_present=true`, `showroom_readiness_present=true`)으로 B2B API+쇼룸 패키지 전달 준비 상태 고정. |
| 2026-04-30 (Track C 외부 제출 1페이지 생성) | `scripts/build_mkm_trackc_external_onepager_v1.py` 추가/실행. 산출 `docs/final/artifacts/mkm_trackc_external_onepager_latest.json/.md` 생성(`status=APPROVED_FINAL_V2`, `decision_state=WATCH`, `go_no_go=GO`)으로 외부 전달용 요약본을 패키지 기반으로 고정. |
| 2026-04-30 (Track C API 명세 패키지 자동화) | `scripts/build_mkm_trackc_api_spec_package_v1.py` 추가/실행. 산출 `docs/final/artifacts/mkm_trackc_api_spec_package_latest.json/.md` 생성(요청/응답 계약, 에러 fallback, TTL/SLA 가드레일 포함)으로 고객 제출용 API 명세를 운영 아티팩트 기반으로 고정. |
| 2026-04-30 (Track C 고객 전달 handoff 패키지 생성) | `scripts/build_mkm_trackc_client_handoff_package_v1.py` 추가/실행. 산출 `docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json/.md` 생성(`packet_status=READY`, 전달 체크리스트 all true)으로 원페이지+API명세+증거경로 단일 핸드오프 묶음 완성. |
| 2026-04-30 (Track C 일일 자동갱신 연결) | `scripts/Invoke-MkmAiV2DailyReadiness.ps1`에 Track C 4종 빌더(상업화 패키지/외부 원페이지/API 명세/handoff 패키지) 연동. 일일 러너 실행 `exit 0`에서 readiness PASS·`GO_FINAL_V2`·`APPROVED_FINAL_V2` 및 Track C 최신 산출물 전부 자동 갱신 확인. |
| 2026-04-30 (Track C 하드 가드 헬스체인 연동) | `scripts/check_mkm_trackc_client_handoff_guard.py` 추가 및 `scripts/run_workspace_automation_health.ps1`에 `-IncludeMkmAiTrackCHandoffGuard` 옵션 연동. 스모크 실행에서 `TRACKC HANDOFF GUARD: PASS`와 가드 리포트 `docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json` 생성 확인. |
| 2026-04-30 (Track C 하드 가드 일일 러너 직결) | `scripts/Invoke-MkmAiV2DailyReadiness.ps1` 말단에 `check_mkm_trackc_client_handoff_guard.py` 실행을 추가해 생성 후 즉시 검증하도록 고정. 일일 러너 실행에서 `TRACKC HANDOFF GUARD: PASS` 및 가드 리포트 최신 갱신 확인. |
| 2026-04-30 (Track C 운영 점검+제출 Freeze 로그) | 스케줄러 `MKM_AIV2_DailyReadiness`/`MKM_AIV2_FinalOpsGuard_Daily` 상태 `Ready` 및 다음 실행시각 확인, 헬스체인 프로필(ready/final/trackc guard) `ALL OK` 재검증. `scripts/build_mkm_trackc_delivery_freeze_log_v1.py` 추가/실행으로 제출 기준본 3종 SHA256 freeze 로그 `docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json/.md`를 `status=FROZEN`으로 생성. |
| 2026-04-30 (스케줄러 즉시 실행 검증 완료) | `schtasks /Run`으로 `MKM_AIV2_DailyReadiness`·`MKM_AIV2_FinalOpsGuard_Daily`를 수동 트리거해 첫 실동작을 즉시 검증. `Last Run Time=2026-05-01 00:18:18`, `Last Result=0` 양쪽 모두 확인, 로그 `reports/mkm_ai_v2_readiness_log.jsonl`/`reports/mkm_ai_final_ops_guard_log.jsonl` append 정상. |
| 2026-04-30 (Track C 원클릭 인수 체인 추가) | `scripts/run_mkm_trackc_operational_acceptance.ps1` 추가. daily readiness + health profile(v2/final/trackc) + freeze log를 원샷 실행해 `docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json`에 `status=PASS`와 근거 경로를 고정. |
| 2026-04-30 (스케줄러 드리프트 4건 정리 + 복구 드릴 PASS) | `reconcile_automation_registry.ps1 -Enforce` 실행으로 drift `4→0`(critical `1→0`) 및 `fixed_count=4` 확인. 이어 `scripts/run_mkm_trackc_guard_recovery_drill_v1.py`로 Track C `FAIL(packet_status_not_ready) → rebuild → PASS` 드릴 수행, 리포트 `docs/final/artifacts/mkm_trackc_guard_recovery_drill_latest.json`에서 `status=PASS` 검증. |
| 2026-04-30 (Track C 운영 대시보드 추가) | `scripts/build_mkm_trackc_ops_dashboard_v1.py` 추가/실행으로 단일 대시보드 `docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json/.md` 생성. 현재 스냅샷 `system=APPROVED_FINAL_V2`, `decision=GO_FINAL_V2`, `packet=READY`, `guard=true`, `acceptance=PASS`, `freeze=FROZEN`, `drill=PASS`를 한 파일에서 집계 확인. |
| 2026-04-30 (대시보드 자동갱신 체인 고정) | `Invoke-MkmAiV2DailyReadiness.ps1`에 `build_mkm_trackc_ops_dashboard_v1.py` 호출 추가, `run_mkm_trackc_operational_acceptance.ps1`에도 대시보드 스텝+evidence(`ops_dashboard`)를 포함하도록 확장. 인수 체인 재실행 PASS 및 acceptance 아티팩트 최신 `generated_at_utc`/`ops_dashboard` 필드 반영 확인. |
| 2026-04-30 (Executive 대시보드 자동화) | `scripts/build_mkm_trackc_ops_dashboard_exec_v1.py` 추가/실행으로 공유용 요약 `docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md` 생성. Daily/Acceptance 체인에 exec 대시보드 스텝을 연결하고 acceptance evidence에 `ops_dashboard_exec`를 추가해 자동 갱신 고정. |
| 2026-04-30 (운영 종료 체크리스트 자동화) | `scripts/build_mkm_trackc_operations_runbook_checklist_v1.py` 추가/실행으로 `docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.json/.md` 생성. Acceptance 체인에 runbook 체크리스트 스텝을 연결하고 evidence에 `operations_runbook_checklist` 경로를 포함해 최종 운영 점검 1장 자동 갱신 고정. |
| 2026-04-30 (Gemini JAMS 이식용 MKM 코어 프롬프트) | JAMS/Athena 협업 주입본 `docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V1.md` 생성. 철학층(소우주·수치화 감정) + 운영층(Fact-Lock/A-B 격벽/레짐 계약) + 실행층(대시보드·acceptance 게이트) + 안전 에스컬레이션 규칙을 한 장으로 고정. |
| 2026-05-01 (채팅 복원 스타터 팩 자동화) | `scripts/build_mkm_chat_resume_pack_v1.py` 추가/실행으로 `docs/final/artifacts/mkm_chat_resume_pack_latest.json/.md` 생성. Acceptance 체인에 `Chat resume pack` 단계와 evidence(`chat_resume_pack`)를 포함해 새 채팅 복구 기준(중앙메모리·대시보드·핵심 명령) 자동 갱신 고정. |
| 2026-05-01 (Genius completion fast-transition 고정) | 스케줄러 헬스체인에 `-FastTransition` 스위치를 추가해 임시 완화 임계치(48h 안정/24h hold recurrence)를 별도 경로로 분리 적용, 즉시 실행에서 `completion_gate=PASS`, `completion_ready=true`, `completion_eta=TRACKING` 전환 및 통합 대시보드 `GO` 유지를 확인. |
| 2026-05-01 (Paddle 런북 대시보드 증거 연결) | `build_mkm_trackc_ops_dashboard_v1.py`에 `paddle_runbook_present` 및 evidence `PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md`를 추가하고, `run_mkm_trackc_operational_acceptance.ps1` evidence에 `paddle_onboarding_runbook` 경로를 포함. 인수 체인 재실행 PASS에서 대시보드 `paddle_runbook_present=true`와 acceptance evidence 반영 확인. |
| 2026-05-01 (Paddle 진행상태 필드 자동화) | `scripts/build_paddle_onboarding_status_v1.py` 추가로 `paddle_onboarding_status_latest.json/.md`를 생성(`RUNBOOK_READY` 기본). Daily/Acceptance 체인에 status 생성 스텝을 연결하고 대시보드 `trackc.paddle_onboarding_status` + evidence `paddle_onboarding_status`를 포함해 결제 온보딩 진행상태 추적을 고정. |
| 2026-05-01 (Paddle 상태 보존 로직 보강) | `build_paddle_onboarding_status_v1.py`를 수정해 인자 미지정 시 기존 상태를 유지하도록 개선(기본값 덮어쓰기 방지). `IN_PROGRESS` 수동 설정 후 acceptance 체인 재실행에서도 대시보드 `paddle_onboarding_status=IN_PROGRESS` 유지를 확인. |
| 2026-05-01 (Paddle 상태 전환 원클릭 추가) | `scripts/Set-PaddleOnboardingStatus.ps1` 추가로 운영자가 상태값을 안전하게 갱신하도록 고정. `PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md` 명령 시퀀스와 `mkm_chat_resume_pack_latest.md` 복구 명령에 상태 전환 커맨드를 반영하고 acceptance PASS 재검증. |
| 2026-05-01 (Paddle 상태 VERIFICATION_PENDING 반영) | `Set-PaddleOnboardingStatus.ps1 -Status VERIFICATION_PENDING` 실행 후 acceptance 체인 PASS 재검증. `paddle_onboarding_status_latest.md`와 `mkm_trackc_ops_dashboard_latest.md`에서 상태가 `VERIFICATION_PENDING`으로 반영된 것 확인. |
| 2026-05-01 (Paddle 완료승격 원클릭 체인) | `scripts/Invoke-PaddleCompletionPromotion.ps1` 추가로 dry/apply 승격 절차를 한 번에 실행 가능하게 고정. 런북에 one-click 명령을 반영했고 dry 실행에서 `ready_to_promote=true`, `applied=false` 리포트(`paddle_onboarding_completion_promotion_latest.json`) 갱신 확인. |
| 2026-05-01 (Paddle COMPLETED 승격 가드 추가) | `scripts/promote_paddle_onboarding_completed_v1.py` 추가로 COMPLETED 전환 전에 acceptance PASS·handoff guard PASS·현재상태 `VERIFICATION_PENDING`을 점검하도록 고정. 런북에 dry/apply 명령을 반영했고 dry-run 결과 `ready_to_promote=true` 보고서 `paddle_onboarding_completion_promotion_latest.json` 생성 확인. |
| 2026-05-01 (Paddle COMPLETED 자동 적용) | `Invoke-PaddleCompletionPromotion.ps1 -Apply` 실행으로 승격 가드 통과 후 `paddle_onboarding_status=COMPLETED` 적용 및 post-promotion acceptance PASS 재검증 완료. 최신 대시보드 `mkm_trackc_ops_dashboard_latest.json`에 `paddle_onboarding_status=COMPLETED` 반영 확인. |
| 2026-05-01 (야간 운영 안정성 재검증) | `run_mkm_trackc_operational_acceptance.ps1` 재실행과 스케줄러 즉시 드릴(`MKM_AIV2_DailyReadiness`/`MKM_AIV2_FinalOpsGuard_Daily`)을 수행해 `LastResult=0`, `TRACKC ACCEPTANCE PASS`, `FINAL OPS GUARD PASS`, `HANDOFF GUARD PASS`, `freeze=FROZEN`을 재확인하고 운영 상태를 `APPROVED_FINAL_V2/GO_FINAL_V2`로 유지. |
| 2026-05-01 (사상 4-Agent 충돌 모델 의사결정 고정) | 철학 논의를 운영 정의로 정리: **제5 체질 신설이 아니라 `The Absolute Balance` 조율 상태**로 규정, 특허/논문 추진은 즉시 확정 대신 **B-track 2단계 격리 검증 선행**(편향 주입/충돌 정량화/소음 veto/레짐 전환 MDD 유의성) 원칙으로 잠금. |
| 2026-05-01 (사상 4-Agent B-track 1차 러너 구현/실행) | `scripts/run_sasang_4agent_collision_btrack_protocol_v1.py` 신설(편향 주입·충돌 분산·소음 veto·MDD 부트스트랩 p-value). 합성/실슬라이스 어댑터(`--use-real-slice`, 입력 `btc_time_machine_regime_switch_backtest_latest.json`) 실행 결과 MDD 개선은 관측되나 p-value 미통과로 `HOLD` 고정(`sasang_4agent_collision_btrack_protocol_latest.json`). |
| 2026-05-01 (사상 4-Agent 실시계열 직결 2차) | 러너에 `--use-timeseries-file`(CSV/JSONL close 파싱) 어댑터를 추가해 `reports/constitution/btrack_pilot/blind_replay/kospi_proxy_ohlcv_from_training_result.csv`로 재실행. MDD 개선은 크지만(`reduction_abs>0`) 표본 `ticks=99`·p-value 미통과로 `HOLD` 유지, `sample_size_warning_low_ticks=true` 안전 가드 잠금. |
| 2026-05-01 (사상 4-Agent BTCUSDT 장시계열 3차) | `reports/constitution/btrack_pilot/blind_replay/btcusdt_1d_2018_2026.csv`(ticks=2966)로 재실행. 쌍체 permutation 유의성(`mdd_reduction_p_value_permutation=0.0005`)을 추가해 `statistical_significance_pass_p_lt_0_05=true`, B-track 판정 `GO_CANDIDATE` 확보(여전히 `research_only`·A-track 자동승격 금지). |
| 2026-05-01 (사상 4-Agent 특허 브리프 자동생성) | `scripts/build_sasang_4agent_patent_brief_v1.py` 추가로 최신 B-track 결과를 근거 패킷(`sasang_4agent_patent_brief_latest.json/.md`)으로 고정. 핵심 청구 포인트(편향 주입·충돌 분산·비대칭 veto·조율 상태)를 evidence 수치와 함께 문서화. |
| 2026-05-01 (사상 4-Agent 발명신고서 초안 자동화) | `scripts/build_sasang_4agent_invention_disclosure_v1.py` 추가로 청구항 중심 초안(`sasang_4agent_invention_disclosure_latest.json/.md`) 생성. 독립항+종속항(편향 주입·충돌 metric·비대칭 veto·조율 상태 비체질 규정)과 실증 근거(`ticks=2966`, `p_permutation=0.0005`)를 단일 문서로 고정. |
| 2026-05-01 (사상 4-Agent 승격 게이트 생성) | `scripts/build_sasang_4agent_promotion_gate_v1.py` 추가/실행으로 승격 판정 아티팩트(`sasang_4agent_promotion_gate_latest.json/.md`) 생성. 체크 통과 시 `A_TRACK_PROMOTION_CANDIDATE_READY`를 부여하되 `human_review_gate_required=true`, `auto_bridge_allowed=false`로 자동 실전 반영을 차단. |
| 2026-05-01 (사상 4-Agent 인간 승인 반영) | 사용자 명시 승인 후 `scripts/promote_sasang_4agent_with_human_approval_v1.py` 실행. 승인 기록(`sasang_4agent_human_approval_latest.json/.md`) 생성 및 승격 게이트를 `A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL`로 전환(`human_review_gate_required=false`, `auto_bridge_allowed=true`)해 승인 증적을 고정. |
| 2026-05-01 (사상 4-Agent Track A 제어 브리지 + 모니터/롤백 준비) | `run_sasang_4agent_tracka_bridge_v1.py`로 제어형 섀도우 브리지(`shadow_ratio=0.1`, `max_live_risk_fraction=0.05`) 활성화, `build_sasang_4agent_monitor_snapshot_v1.py`로 상태 스냅샷 생성(`alert=false`, `KEEP_CONTROLLED_BRIDGE`). 동시에 원커맨드 롤백 `invoke_sasang_4agent_force_hold_v1.py`를 추가해 긴급 `FORCE_HOLD` 스위치 준비 완료. |
| 2026-05-01 (사상 4-Agent 일일 모니터 자동화 고정) | `Invoke-Sasang4AgentDailyMonitor.ps1` + `Register-Sasang4AgentDailyMonitorTask.ps1` 추가 및 태스크 `SASANG_4AGENT_DailyMonitor` 등록(07:40). 수동 러너+즉시 스케줄 실행 검증에서 `LastTaskResult=0`, 아티팩트 `sasang_4agent_daily_monitor_run_latest.json(status=PASS)`·`sasang_4agent_monitor_snapshot_latest.json(alert=false)` 확인. |
| 2026-05-01 (사상 4-Agent FORCE_HOLD 복구 드릴 PASS) | `invoke_sasang_4agent_force_hold_v1.py --reason drill_2026-05-01`로 즉시 차단 후, 승인 재반영+브리지 재가동+모니터 갱신을 수행. 요약 드릴 `build_sasang_4agent_force_hold_recovery_drill_v1.py`에서 `status=PASS`(`force_hold_applied`, `gate_recovered_to_promoted`, `bridge_active_after_recovery`, `monitor_alert_false` 전부 true) 확인. |
| 2026-05-01 (사상 4-Agent 제출 번들 단일화) | `build_sasang_4agent_promotion_submission_bundle_v1.py` 추가/실행으로 최종 제출 번들 `sasang_4agent_promotion_submission_bundle_latest.json/.md` 생성. 상태 문구 `PROMOTED_WITH_HUMAN_APPROVAL + MONITORING_ACTIVE + DRILL_PASS`와 핵심 9개 아티팩트 SHA256을 한 장으로 고정. |
| 2026-05-01 (독립 재현 1회 반영) | `kospi_proxy_ohlcv_from_training_result.csv`로 독립 재현 아티팩트(`sasang_4agent_collision_btrack_protocol_repro_kospi_latest.json`) 생성 후 제출 번들에 `repro_check` 필드 추가. 유의성/개선은 통과했으나 표본 `ticks=99`로 `repro_sample_size_ok=false`, 번들 상태를 `HOLD_OR_INCOMPLETE_CHAIN`으로 보수 전환. |
| 2026-05-01 (독립 재현 표본 300+ 충족 복구) | 재현 입력을 `research/market_data/kospi_daily_external_yf.csv`로 교체해 `sasang_4agent_collision_btrack_protocol_repro_kospi_latest.json` 재생성(`ticks=7232`, `p_permutation=0.017`, `sample_size_warning_low_ticks=false`). 제출 번들 재생성 후 `repro_check_pass=true`, 최종 상태 `PROMOTED_WITH_HUMAN_APPROVAL + MONITORING_ACTIVE + DRILL_PASS`로 복귀. |
| 2026-05-02 (MKM Lab · LinkedIn B2B 실행 번들) | 개인 프로필 영문 우선 About·스페셜 픽스·주간 운영 노트 톤 유지; 추적 `reports/linkedin_dm_outreach_tracker_v1.tsv`, 복붙 `reports/linkedin_dm_copypaste_bundle_v1.txt`(KR+EN 첫 DM A/B/C·7일 팔로업). DM/게시는 본인 LinkedIn 세션에서만 수행. |
| 2026-05-02 (VPS · bitcoin-trading · 체결→cursor_trade_history) | 로컬 커밋만 있으면 VPS에 파일 MISSING — **`git@github.com:mkmlab-v2/mkm-destiny-ai-41e38ec6.git`의 `fix/btrack-ohlcv-cli-help-and-eval-wrapper-github`**에 반영 필요(비FF 시 worktree+체리픽 후 푸시). 체인: `export_binance_fills_to_cursor_trade_history_v1.py`→`sync_cursor_trade_history_latest_24h.py`; 등록 `ops/v2/ssh/register_export_then_sync_cursor_trade_history_cron.sh`, cron 태스크 `bitcoin-binance-export-then-cursor-trade-history`, 로그 `/var/log/bitcoin_export_then_cursor_trade_history.log`, **`WORKSPACE_ROOT=/opt/mkm-lab-workspace-v2/projects/bitcoin-trading`**. 브랜치 전환 전 **`projects/no1kmedi` 등 로컬 수정은 stash**. **재발 방지 SSOT:** `projects/bitcoin-trading/ops/v2/DEPLOY_GIT_POINTER_V1.json` + 스모크 `bash ops/v2/ssh/check_vps_deploy_files_vs_pointer.sh`. **▶ PM2/본선 혼동 방지는 본 파일 「VPS · 비트코인 본선」절(크로스 채팅 고정).** |
| 2026-05-03 (VPS `vps-mkmlife` · PM2 이름 실측) | 동 호스트 `pm2 list` 기준 **24h 온라인 앱명 `bitcoin-live-small-24h`** — 런북 예시 `bitcoin-live` 와 불일치할 수 있음. **`verify_and_reload` FF 실패**는 다수 **VPS가 `main`이 아닌 브랜치에 checkout** 된 경우와 합치됨 → 본선을 main에 맞출지·feature를 유지할지 **정책 분리** 후 조치. |
| 2026-05-04 (Track B 시계 정렬 + 예언 복기 레이어) | `docs/final/artifacts/trackb_weekly_gate_recheck_latest.json` `generated_at_utc=2026-05-04T06:07:21Z`, `decision=GO_RESEARCH`, `out_of_scope` 유지(연구·본선 합선 없음). 예언 조립: `scripts/eval_btrack_prophecy_post_mortem_v1.py`→`btrack_post_mortem_latest.json`; 얇은 헬스 `scripts/check_btrack_4h_health_v1.py`·`scripts/Register-Btrack4hHealthTask.ps1`. **히트레이트 60%대는 목표** — 달성·회귀 주장은 `eval_prophecy_hit_rate_v1`·고정 eval 세트로만(Fact-Lock). |
| 2026-05-04 (압축↔B-track 번들 연결 SSOT) | `build_btrack_llm_input_bundle.py` v1.2.0에 `compression_bridge_context` 슬롯(`ultra_compression_kpi_summary`·`MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1`·`MULTILENS_ULTRA_COMPRESSION_DECISION_V1`)을 추가하고 `build_compression_prophecy_bridge_status_v1.py` 재실행 결과 **`bridge_status=wired_partial_v1`** 전환. 회귀 `tests/test_compression_prophecy_bridge_status_v1.py` 고정; 영향 평가는 별도(문자열/경로 결선 ≠ 적중률 인과 증명). |
| 2026-05-04 (압축 브리지 ON/OFF 인과 프로브) | `build_compression_bridge_impact_probe_v1.py`로 번들 ON/OFF(압축 컨텍스트 제거) 비교를 자동화: `recent_trading_days=30`에서 `prediction_changed=false`, `delta_weighted_score=0.0`, `delta_price_directional_hit_rate=0.0`, `decision=NO_OBSERVED_DIFF`. 현재 결선은 관측 메타 중심이며 예측 가중치 영향은 미발현(Fact-Lock). |
| 2026-05-04 (압축 브리지 가중치 반영 + 재프로브) | `generate_btrack_hypothesis_prophecy_v1.py`에 `compression_bridge_context` 기반 조정(`compression_bridge_adjustment`)을 추가해 `weighted_score_raw`와 분리 기록. 재프로브(`recent_trading_days=30`) 결과 `prediction_changed=true`, `delta_weighted_score=-0.008658`, `delta_price_directional_hit_rate=0.0`, `decision=OBSERVED_DIFF` — 방향/신뢰도·가중치에는 영향이 생겼지만 hit-rate 개선 인과는 미증명. |
| 2026-05-04 (브리지 조정 민감도 스윕) | `run_compression_bridge_adjustment_sweep_v1.py` 추가로 `signal_scale x positive_signal_cap` 그리드(5x3) 평가. `signal_scale=0`은 `NO_OBSERVED_DIFF`, `signal_scale>=0.5`는 `delta_weighted_score`/confidence 변화(`OBSERVED_DIFF`)가 재현되지만 `delta_price_directional_hit_rate`는 전 구간 `0.0`(30일) — 현재 조정은 예측 민감도만 바꾸고 가격 적중률 uplift는 미확인. |
| 2026-05-04 (브리지 방향 전환 스윕) | `run_compression_bridge_directional_impact_sweep_v1.py`로 `signal_scale x negative_signal_cap x tie_break_min_margin`(5x4x3=60) 탐색: `direction_changed_rows=6`까지 확보했지만, 해당 행은 `on_prediction_direction=neutral` 전환과 함께 `delta_price_directional_hit_rate=-0.566667`로 악화. best hit 후보는 `signal_scale=20, negative_cap=0.1, margin=0.03`에서 `delta_hit_rate=0.0`(confidence만 하락). 결론: 현재 브리지 조정은 방향 전환 가능하나 hit-rate uplift 근거는 없음. |
| 2026-05-04 (고변동 neutral 전환 가드 재검증) | `generate_btrack_hypothesis_prophecy_v1.py`에 `compression_bridge_block_neutral_flip_on_high_vol`(기본 on) + `recent_abs_return_mean` 기반 가드를 추가했으나, 동일 60-grid 재실행 결과 `direction_changed_rows=6`·`delta_price_directional_hit_rate=-0.566667` 패턴이 유지. 가드 단독으로는 악화 구간 제거 실패; 다음 단계는 bridge 신호를 direction 결정이 아닌 confidence/size-only 레인으로 격리 검토. |
| 2026-05-04 (브리지 direction 분리 적용) | `generate_btrack_hypothesis_prophecy_v1.py`를 direction-isolation 모드로 전환: bridge는 `weighted/margin/neutral_penalty`를 건드리지 않고 `prediction.confidence`만 조정(`compression_bridge_confidence_adjustment`). 재실행 결과 `compression_bridge_directional_impact_sweep_latest.json`에서 `direction_changed_rows=0`, `delta_price_directional_hit_rate` 악화 행 제거; `prediction_changed=true`는 confidence 차이만 의미. |
| 2026-05-04 (confidence→size 계량 추가) | `build_compression_bridge_impact_probe_v1.py`에 `size_policy`(`confidence_only_scalar_v1`)를 추가해 ON/OFF의 `size_scalar`·`payoff_mean_size_weighted`를 비교. 현재 스냅샷은 `delta_size_scalar=-0.0086`, `delta_size_weighted_payoff_mean=-3.604e-05`, `delta_hit_rate=0.0` — 브리지 영향은 size/confidence 레인에서만 관측되고 방향·적중률 인과는 없음. |
| 2026-05-04 (size 룰 고정 + 고정 윈도우 홀드아웃 체인) | `btrack_lens_ensemble_v1.json`에 `compression_bridge_size_mode=confidence_only_scalar_v1`, `size_floor=0.1`, `size_cap=1.0`, `neutral_size_scalar=0.0`를 고정하고, `run_compression_bridge_size_holdout_eval_v1.py`를 추가해 30/60/120일 고정 윈도우 ON/OFF 평가를 자동화. 최신 `compression_bridge_size_holdout_eval_latest.json` 기준 `direction_changed_rows=0`, `hit_rate_uplift_rows=0`, `size_weighted_payoff_uplift_rows=0`로 아직 승격 근거는 미충족(HOLD). |
| 2026-05-04 (size 브리지 튜닝 스윕 + 승격 가드 GO 후보) | `generate_btrack_hypothesis_prophecy_v1.py` 신호식을 `quality_bonus - policy_gap_penalty`로 확장하고, `run_compression_bridge_size_tuning_sweep_v1.py`/`check_compression_bridge_size_promotion_gate_v1.py`를 추가. 베스트(`signal_scale=2.0`, `negative_cap=0.0`, `quality_bonus_scale=0.4`, `policy_gap_penalty_scale=0.1`)를 `btrack_lens_ensemble_v1.json`에 반영 후 30/60/120일 재검증에서 `direction_changed_rows=0`, `mean_delta_size_weighted_payoff=+0.00013029`, 게이트 `GO_SIZE_LANE_PROMOTION_CANDIDATE` 확보. |
| 2026-05-04 (size 브리지 walk-forward 확정) | `run_compression_bridge_size_walkforward_eval_v1.py`(30→210일, 30일 스텝) 추가 후 `check_compression_bridge_size_promotion_gate_v1.py`를 holdout+walk-forward 이중게이트로 강화. 최신 결과 `direction_changed_rows=0`, `min_delta_hit_rate=0.0`, `min_delta_size_weighted_payoff=+0.00012027`, 최종 `GO_SIZE_LANE_PROMOTION_CONFIRMED` 달성(여전히 size-only 레인, 방향 개입 없음). |
| 2026-05-04 (size 브리지 일일 자동 게이트 엔트리) | `run_compression_bridge_size_daily_gate_v1.ps1`를 추가해 holdout→walk-forward→promotion gate를 일괄 실행하고 `compression_bridge_size_daily_gate_summary_latest.json`를 생성. 등록 스크립트 `Register-CompressionBridgeSizeDailyGateTask.ps1` 추가(기본 07:20). 수동 1회 실행 결과 `status=PASS`, `decision=GO_SIZE_LANE_PROMOTION_CONFIRMED`. |
| 2026-05-05 (메타 인지 봉투 v1 + NotebookLM Vault 미러) | 스키마 `mkm_meta_layer_turn_envelope_v1`·`scripts/mkm_meta_layer_envelope_v1.py`(validate/append/audit-markdown)·fixture·`pytest tests/test_mkm_meta_layer_envelope_v1.py` **8 passed**·CI `dual-regime-integrity`+`run_fact_lock_bundle` 3d·Track C `Invoke-TrackCMacroDailyFusion_v1.ps1` **`-MetaLayerEnvelopePath` 선택**(비면 미실행)·`reports/agent_decisions_log.jsonl` 일반 vs `meta_layer_envelope_v1` 분기 **AGENTS** 명시; Fact-Lock 본문 **`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.3.1**. **`sync_notebooklm_sources_to_mkm_data_vault.ps1` exit 0** `copied=104 skipped=91` → `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources` OK. |
| 2026-05-05 (명리 렌즈 고도화 v1 — CENTRAL 잠금) | 만세력(`birth_instant_utc`+IANA·native 스모크·`athena-manseryeok`) + §3.3 결정론 스택 + AI 봉투(B-track) + **삼고**(입력·엔진·출력) 수학화 + 날씨/일반예언은 **원리만 차용·데이터 합선 금지**를 본 파일 전용 절로 고정; 구현 확장은 여전히 `CONSTITUTION` 표·pytest만 SSOT. |
| 2026-05-05 (명리 Sprint-1 base vector lock) | `scripts/myeongri_jijangan_ohang_v1.py`에 `build_myeongni_core_vector_v1` 추가(지장간 tier 포함 element raw count + normalized strength + overlay), 스키마 `docs/final/artifacts/schemas/myeongni_core_vector_v1.schema.json` 신설, `tests/test_myeongri_jijangan_ohang_v1.py`에 결정론·스키마 검증 회귀 추가, `scripts/myeongri_complete_fusion.py`에 `myeongni_core_vector_v1` 출력 연결, P0 경로 게이트 266·관련 pytest 통과. |
| 2026-05-05 (명리 Sprint-2 timeline lock) | `scripts/myeongri_daewoon_timeline_v1.py` 신설(起運 `qiyun_v1` + `daewoon_v1` 연동, `as_of_utc` 기준 활성 cycle 계산), 스키마 `docs/final/artifacts/schemas/myeongri_daewoon_timeline_v1.schema.json`·회귀 `tests/test_myeongri_daewoon_timeline_v1.py` 추가(경계 정책: `start<=age<end`, 말단 초과는 마지막 cycle), `verify_p0_constitution_gate_paths.ps1`에 경로 반영 후 P0 269·관련 pytest 통과. |
| 2026-05-05 (사상12 통합 게이트 vs A-Track 승격) | `sasang12_promotion_candidate_gate_latest.json`(unified)에서 **`status=PASS`여도 `track_wall.promotion_to_a_track_allowed=false`** — 통합 PASS≠방향 A본선 승격. v2~v10 개별 `*_gate_vN_*` FAIL 기록과 **`track_wall`** 필드를 함께 볼 것. 헌법 **`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.5** 표에 해석 행 반영. |
| 2026-05-05 (대외 보안·IP·카피 SSOT) | `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`·`TRACK_C_IP_BUSINESS_PLAN` → P0·**CLAUDE** 도메인 핸드오프·**JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC** 관련 정책 단락·헌법 **§1.1.3**·`AGENTS`·**NO1KMEDI** §10 양방향 고정. |
| 2026-05-05 (도메인×쇼룸 표 — 장기기억 루틴) | **`MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1** 신설: jemaai=전광판·관측 데모, mkmlife=원퀘스천 리포트, jema-ai.com=브랜드 허브·링크; **CENTRAL**에 «에이전트 반복 루틴» 표 추가·헌법 §1.1.3·P0 경로·CLAUDE/AGENTS 교차. |
| 2026-05-05 (허브 CTA 초안) | **`MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` §1.1b** — jema-ai→jemaai/mkmlife/a-codeai **버튼 라벨 초안**표; `JEMA_AI_DOMAIN_POINTER_V1.md` §4.1 교차; P0에 `JEMA_AI_DOMAIN_POINTER` 경로 추가. |
| 2026-05-05 (jema-ai.com 구현 연결) | `projects/no1kmedi/marketing-site/public-copy.json` **`hub_links.showroom_jemaai`** + `page.tsx` 바인딩; 스키마 `check-public-copy-schema.mjs` 갱신; `page.tsx` **`homepagePresetClass`** 누락 타입오류 수정·`npm run build` OK; Track C §3.6·`MKM_DOMAIN` 구현 원천 문장 동기. |
| 2026-05-05 (BTC 선물 아론 엔진 본선 전환) | `bitcoin-live-small-24h` 런타임을 `aroon_v1`로 전환: `start_live_trading.py`(비대화형 위임)·`scripts/start_24h_daemon.py`(.env 우선순위 보정)·`src/futures_engine/*`·`src/api/binance_client.py`·`src/monitoring/trading_prometheus.py`/`trading_otel.py`를 VPS 동기화 후 `pm2 restart --update-env` + `pm2 save`; 본선 `.env`에 `SYMBOL=BTCUSDT`, `TESTNET=false`, `ENABLE_TRADING=true`, `BTC_FUTURES_ENGINE=aroon_v1`, `AROON_*` 고정. 상태 확인: PM2 online, `trading_state.json`=`schema trading_state_aroon_v1`·`engine aroon_v1`·`last_signal HOLD`·`trades_count 0` (실주문 체결은 아직 없음). |
| 2026-05-04 (RDA 스마트팜 공공 데이터) | 농진청 제공 ZIP 로컬 전개·컬럼 실측: 기상 시간자료(`지점명`·`일시`·온도·습도·일사량·강수량`, 다중 시트), 토양검정 화학성 연도별 xlsx(2025는 `skiprows=1`); 매핑·4주 로드맵·계약 갭(토양수분 미제공→텔레메트리 필수)을 `docs/final/SMARTFARM_RDA_SOIL_WEATHER_MAPPING_AND_ROADMAP_V1.md` + `SMARTFARM_RDA_COLUMN_MAP_V1.json`에 고정; 대용량 전개 경로 `data/smartfarm_rda_extract_v1/`는 `.gitignore`. Week2는 `scripts/build_smartfarm_zone_weather_features_v1.py`로 station→zone 매핑 + `rain_mm_12h` 리플레이 입력(`zone_weather_replay_inputs_v1.csv`)까지 검증, Week3는 `scripts/evaluate_smartfarm_rain_gate_kpi_v1.py`로 임계값 스윕(`rain_gate_threshold_sweep_v1.csv`)·요약(`rain_gate_threshold_sweep_summary_v1.json`) 생성, Week4는 `scripts/check_smartfarm_week4_data_guard_v1.py`·`scripts/build_smartfarm_week4_ops_dashboard_v1.py`로 가드/대시보드 산출(`smartfarm_week4_ops_dashboard_v1.json`)까지 연결, 후속으로 `scripts/build_smartfarm_gap_incident_report_v1.py`로 gap incident 24건(`gap_incident_report_v1.csv`) 자동 추출 + `scripts/simulate_smartfarm_gap_recovery_policy_v1.py`로 FFILL/SKIP/FLAG 보정정책 비교(`gap_recovery_policy_simulation_v1.csv`) + `scripts/evaluate_smartfarm_gap_policy_impact_v1.py`로 hybrid(skip+small ffill) 전/후 KPI 영향(`gap_policy_kpi_impact_v1.csv`) + `scripts/build_smartfarm_recommended_gap_policy_v1.py`로 운영 권장안(`recommended_policy_v1.json`) 자동 결정 + `scripts/run_smartfarm_gap_policy_daily_gate_v1.py`로 일일 GO/WATCH/HOLD 판정·알림(`smartfarm_gap_policy_daily_gate_v1.json`) + 프로파일(`daily_gate_policy_profile_v1.json`: conservative/standard/aggressive) 기반 임계치 분기 및 aggressive 이중조건 override(max_gap + incident_count)까지 연결. |
| 2026-05-02 (MKM 자체 LLM·이론 체화 — 전략 지문 고정) | 규칙/프롬프트 정렬 vs 가중치 학습 **층 분리**; 고도화 기본은 **규칙+RAG+게이트**. 로컬 젬마 등 **체화형 파인튜닝**은 eval·데이터·프롬프트 비대가 **실측**될 때만 ROI 검토 — 미달이면 오버엔지니어링. 재질의 시 **`CENTRAL_AGENT_MEMORY_V1` 「MKM AI 고도화 · 자체 LLM」** 절 우선. |

---

## 작업 맥락 레슨 (커밋·경로 기반 1차 초안)

> **목표:** 과거를 **100% 복원**하는 것이 아니라, **우선순위·격벽·톤·결정 맥락**이 끊기지 않게 유지한다. 날짜·수치·구현 여부는 Fact-Lock·스크립트로만 확정하고, NotebookLM·브리핑은 **맥락 보강**에 쓴다.  
> 근거: `git log` (2026-03~04), `memory_revival_gap_scan_latest.json`. **2025-05~2026-02**는 이 레포에 커밋이 거의 없어 **여기만으로 서사 복원 불가** — 다른 레포·메모·NL 내보내기로 보강.

### 복구 맥락 운영 체크리스트 (이 채팅 기준)

1. 목표는 과거의 완전 복원이 아니라 **의사결정 연속성(우선순위·격벽·톤·결정 이유)** 유지다.
2. 구현·경로·날짜·수치 확정은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + git + exit code + artifact JSON만 사용한다.
3. `CENTRAL_AGENT_MEMORY_V1.md`에는 **왜 이 선택을 유지하는지**만 압축해 남기고, 미검증 수치는 쓰지 않는다.
4. `CURRENT_OPS_SNAPSHOT.md`에는 **이번 주 실행 상태/결정**만 짧게 남기고, 장기 지문은 본 파일에서 관리한다.
5. 연구 레일(B/실험)과 상용 레일(A/운영)의 자동 합선을 금지하고, 승격은 사전 게이트·증거를 붙인다.
6. 압축 성과는 트랙을 섞지 않고 표기한다(Track A KPI와 ultra-literal 복원 수치를 한 문장으로 합치지 않는다).
7. 장기 공백 구간은 추측으로 채우지 말고, 외부 증거를 수집한 뒤 검증 완료 한 줄만 승격한다.

| 상황 | 당시 패턴(증거) | 앞으로 이렇게 |
|------|-----------------|---------------|
| 품질·회귀 | `ci`/`test`/`fix`가 `feat`/`docs`/`chore`와 함께 꾸준히 섞임 | 작업 전후 **게이트·pytest**를 고정 루틴으로 두고, 브리핑만으로 통과·구현 단정 금지 |
| 운영 가시성 | `docs`·`reports` 파일 터치량이 큼 | `CURRENT_OPS_SNAPSHOT`·`artifacts`를 **한 사이클의 산출 세트**로 취급 |
| 자동화 | `scripts/` 변경이 많음 | 반복은 **스크립트 1개 + exit code**로 고정해 Fact-Lock과 맞춤 |
| 연구 vs 상용 | `feat`·`chore` 병행 | B-track/실험은 **격벽·재현 seed** 유지, 본선·A-track과 **자동 합선 금지** |
| 원격·VPS 혼선 | (동기화 이슈에서 확인) | `git fetch` 후 `origin/main` 정렬, 필요 시 `scripts/Run-GitOriginMainSyncLocalAndVps.ps1`; **bitcoin-trading 운영 스크립트는 HQ 모노레포와 destiny 레포 브랜치가 다를 수 있음** — VPS가 쓰는 브랜치에 커밋이 없으면 pull 후에도 파일 MISSING. |
| 장기 공백 | 스캔상 2025-05~2026-02 무커밋 구간 | 그때의 결정은 **외부 증거**로만 채우고, 본 파일에 **추측 한 줄 금지** |
| NotebookLM 교차질의 | 인용 id가 가리키는 **현재 소스 제목**과 NL 답의 **날짜 서술**이 어긋날 수 있음 (2026-04-15 대조) | “언제 무엇을 확정했다”는 **`nlm source list` 제목·원문 + git**으로 맞춘 뒤에만 승격 |

### NotebookLM 등으로 공백 보강 (운영 절차)

1. **소스:** 해당 기간 내보내기(MD/채팅/다른 레포 요약)를 NL에 올리거나 `docs/NotebookLM_sources_manifest.md`와 정렬.
2. **기록:** `docs/final/artifacts/memory_revival_gap_notes_v1_latest.json`의 해당 `segment`에 `summary_one_line`, `sources`, `verification` 갱신. (기본은 브리핑·**미검증**)
3. **검증:** 구현·경로·수치는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·스크립트로 대조 후 `verified_refs`에 경로만 적는다.
4. **승격:** 검증된 한 줄만 「분기별 한 줄」 또는 「작업 맥락 레슨」표로 옮긴다. 미검증은 SSOT 본문에 **쓰지 않는다**.
5. **스캔 갱신:** `scripts/run_memory_revival_gap_scan.ps1` 실행 → `memory_revival_gap_scan_latest.json`의 해당 gap에 `briefing_overlay`가 붙는지 확인.

---

## 아이덴티티 (운영 톤 3~6줄)

- **역할:** 지휘관 의도 + SSOT + 스크립트 — 환각으로 구현 단정 금지.
- **톤:** 짧고 판정 가능한 문장; 선택지 강요 없이 완료 보고.
- **홍보 프레이밍:** 뇌과학 기반 영감(프레이밍/주의/인지부하)은 대외 과학 주장 근거가 아니라 **설계 원칙**으로만 사용하고, 대외 문장은 항상 `아티팩트 근거 + 면책 + 비단정` 3요소를 포함한다.
- **금지:** 2차 성경 레짐을 실전 트리거에 사용, 멀티렌스 단일화 주장.

## 레인별 진행 (한 줄씩)

| 레인 | 상용/게이트 상태 (한 줄) | 마지막으로 본 산출/경로 |
|------|---------------------------|-------------------------|
| 성경 | | |
| 명리 | **고도화 v1:** 본 파일 「명리 렌즈 고도화 v1」— 삼고·만세력·§3.3 스택·날씨 원리 격리. 체인: `run_myeongni_lens_chain_from_bot_v1.py`/`Run-MyeongniLensChainFromBot_v1.ps1`; 단일 렌즈 `--recommended` 또는 브리지. | §3.3·`tests/test_myeongni_lens_chain_from_bot_v1.py` |
| 사상 | 사상 4-Agent는 A-Track 승격 유지 상태이며 모니터 정책에서 `geumhwa_transition_threshold=0.58`로 상향해 과민 자동주입을 완화했다. | `docs/final/artifacts/sasang_4agent_monitor_policy_v1.json` |
| 퓨전 | `보명지주/성정불변/병증약리/금화교역` 융합 게이트는 `FUSION_GATE_PASS`로 고정되어 승격 체인 체크에 결합됨. | `docs/final/artifacts/sasang_4agent_fusion_gate_latest.json` |

## 지금 막힌 것 (있을 때만)

- 

## 다음에 할 일 (최대 3개)

1. **디스크 동기화가 장기기억의 본체:** 세션 끝마다 의미 있는 전환만 **본 파일·커밋**으로 남기고, NotebookLM·채팅 요약은 **검증 후 한 줄 이관**만(Fact-Lock·표 프로토콜 유지).
2. **일인 개발 Git 고정:** 일상 저장은 `scripts/push-internal.ps1`; `gitea/main`에 합칠 때는 워킹 트리 clean 후 `scripts/SoloDev-MergeFeatureToGiteaMain.ps1`(먼저 `-DryRun`). GitHub는 예외 시만 `Push-GitHub-Explicit.ps1 -Acknowledge`.
3. **게이트 리듬:** `scripts/verify_p0_constitution_gate_paths.ps1`를 주기 점검으로 두고, 시간 허용 시 `scripts/run_fact_lock_bundle.ps1` — B→A 자동 합선·실매매 자동 트리거 없음 전제 유지.

- `reports/bio_sasang_nstates_strict_comparison_v2.json` 재생성: `py scripts/build_bio_sasang_nstates_strict_comparison_rehydrate_v1.py`

## 동기화 루틴

- **자기점검(시작 1줄):** "CENTRAL_AGENT_MEMORY_V1 + athena_memory_bank 참조 완료, Fact-Lock 우선."
- **트리거 자동기동:** 사용자가 「장기기억 토대로 진행해」「CENTRAL 기준으로 진행해」「팩트락 기준으로 자동 처리해」라고 말하면, 에이전트는 먼저 `CENTRAL`·`AGENTS`·`CONSTITUTION_*`를 읽고 관련 `_latest` 아티팩트/체크리스트를 갱신한 뒤 판정(HOLD/GO)까지 진행한다.
- **시작:** 이 파일 **전체** 훑고(특히 **이론 압축 표**) 오늘 작업과 충돌 여부 확인.
- **끝:** 분기 한 줄 / 레인 표 / 막힘만 갱신. 이론 표는 **헌법 변경 시에만** 수정.
- **MCP `memory_*`:** 선택. 단일 SSOT는 본 파일 + `CONSTITUTION_*`.

### 프로토콜 필드 매핑 (작업 종료 로그북)

루트 `.cursorrules` 「Memory Management Protocol」과 동일 목적. **대화 전문·자동 요약 붙여넣기 금지.**

| 라벨 | 본 파일에 넣을 위치 |
|------|---------------------|
| [STATUS] | 「레인별 진행」·「지금 막힌 것」— 진행중/완료/보류를 **한 줄**로 |
| [DECISION] | 「분기별 한 줄」또는 해당 레인 셀 — 선택한 패턴·아키텍처·중단 사유 **팩트만** |
| [NEXT_STEP] | 「다음에 할 일」(최대 3개) |

구현 완료·경로·수치는 **브리핑으로 단정하지 말고** `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·exit code와 대조 후 기록한다.
