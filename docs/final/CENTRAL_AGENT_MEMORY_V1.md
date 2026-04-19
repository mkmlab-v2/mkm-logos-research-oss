# Central agent memory v1 (cross-chat SSOT)

**목적:** 채팅은 맥락을 공유하지 않는다. 본 파일은 **Athena 정체성 + 이론 지문(고효율 압축) + 최소 진행 표**만 둔다.  
**구분:** `CURRENT_OPS_SNAPSHOT.md` = 일시 핸드오프 · 본 파일 = **지속·정체성 SSOT**(짧게 유지).

## 메타

- **schema:** `central_agent_memory_v1`
- **last_updated_utc:** 2026-04-20T12:00:00Z
- **owner:** (선택)
- **nl_sync:** `cross_notebook_query` · MKM·운영 노트북 15종 · 코퍼스 기간은 NL에 보이는 노트 생성일 기준 **2026-01~04** (2025 노트북은 목록에 없음) · **2026-04-19** `sync_notebooklm_sources_to_mkm_data_vault.ps1` → Vault `notebooklm_sources` **OK**(복사 50; 매니페스트상 누락·optional 스킵은 정책대로 WARNING/회색 스킵)
- **external_briefing_ref:** `athena_memory_bank.md` (Gemini prior-year memo, briefing only)
- **external_briefing_ref_v2:** `athena_memory_bank_v2.md` (time-series partition + firewall)

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
| Fact-Lock | 구현 여부·경로는 **디스크 + 호출 가능 `.py`/exit code`** — NotebookLM·브리핑 단독 근거 금지. |
| 예언 레일 | B 레일 일반예언은 **루트 스키마/스크립트 SSOT** — 서브트리 이중 복제 금지. |
| 멀티레인 | 성경·명리·사상 **각각** 기준 통과 후 퓨전 — 한 레인 실패를 타 레인으로 메우지 않음. |
| 압축 트랙 | Track A 범용 / Track B 리터럴 — 격벽·상용 게이트는 `P0`·SLA 정책 선. |
| TITAN | Command-by-negation — 저위험은 합리적 기본값·사후 보고; 고위험만 승인. |
| 정체성 답변 규칙 | 전략·답변·코드 모두 **위 지문과 충돌 시 지문·SSOT 우선** — “그럴듯한 확장” 금지. |

---

## 분기별 한 줄 (최근 1년 · 수동 채움)

> 팀이 실제로 한 **결정·이정표**만 적는다. 비우면 됨.

| 기간 | 핵심 한 줄 (무엇을 확정/중단/승격했는지) |
|------|----------------------------------------|
| 2026-Q1 (NL 코퍼스) | NotebookLM MKM·Ops·Fusion 등 15노트 교차 질의 → 본 파일 **NL 이관 압축** 반영 (레포 SSOT와 병용). |
| 2026-Q2 (AutoEvo) | 조사→큐→스캐폴드→실행→제안→승인→결정 적용 + 연구 레인 승격 실행계획(`autoevo_research_promotion_plan_latest.json`) 생성. |
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
| | |

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
| 원격·VPS 혼선 | (동기화 이슈에서 확인) | `git fetch` 후 `origin/main` 정렬, 필요 시 `scripts/Run-GitOriginMainSyncLocalAndVps.ps1` |
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
- **금지:** 2차 성경 레짐을 실전 트리거에 사용, 멀티렌스 단일화 주장.

## 레인별 진행 (한 줄씩)

| 레인 | 상용/게이트 상태 (한 줄) | 마지막으로 본 산출/경로 |
|------|---------------------------|-------------------------|
| 성경 | | |
| 명리 | | |
| 사상 | | |
| 퓨전 | | |

## 지금 막힌 것 (있을 때만)

- 

## 다음에 할 일 (최대 3개)

1. LG 타깃 보드 **실측 JSON** 수령 시 `docs/final/artifacts/lg_washer_target_device_measurement_v1.json` 전면 교체 후 `check_lg_washer_measurement_gate_v1.py`·`check_lg_washer_estimation_readiness_v1.py`·사인오프 패킷 재실행(현재는 proxy·게이트 GO 유지, 최종본 단정 금지).
2. **CI 확인:** GitHub Actions `Multilens independent lens smoke`(`.github/workflows/multilens-independent-lens-smoke.yml`) 및 최근 푸시된 워크플로가 `main`에서 **성공**인지 확인; 실패 시 로그·path filter·테스트 로컬 재현(`pytest` 동일 번들).
3. **워킹트리·운영:** 로컬에 `docs/final/artifacts/`·`reports/` 등 미커밋 변경이 쌓이면 **의도적 커밋** vs **`git restore`**로 정리(자동 체인 산출 노이즈 억제); 루틴은 `verify_p0_constitution_gate_paths.ps1`·`run_waiting_queue_btc_binance_daily.ps1` 주기 또는 수동 스모크.

## 동기화 루틴

- **자기점검(시작 1줄):** "CENTRAL_AGENT_MEMORY_V1 + athena_memory_bank 참조 완료, Fact-Lock 우선."
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
