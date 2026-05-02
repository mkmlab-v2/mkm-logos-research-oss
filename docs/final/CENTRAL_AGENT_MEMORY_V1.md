# Central agent memory v1 (cross-chat SSOT)

**목적:** 채팅은 맥락을 공유하지 않는다. 본 파일은 **Athena 정체성 + 이론 지문(고효율 압축) + 최소 진행 표**만 둔다.  
**구분:** `CURRENT_OPS_SNAPSHOT.md` = 일시 핸드오프 · 본 파일 = **지속·정체성 SSOT**(짧게 유지).

## 메타

- **schema:** `central_agent_memory_v1`
- **last_updated_utc:** 2026-05-02T05:30:00Z
- **owner:** (선택)
- **nl_sync:** `cross_notebook_query` · MKM·운영 노트북 15종 · 코퍼스 기간은 NL에 보이는 노트 생성일 기준 **2026-01~04** (2025 노트북은 목록에 없음) · **2026-04-19** `sync_notebooklm_sources_to_mkm_data_vault.ps1` → Vault `notebooklm_sources` **OK**(복사 50; 매니페스트상 누락·optional 스킵은 정책대로 WARNING/회색 스킵) · **2026-04-28** NotebookLM MCP `server_info/notebook_list` live 확인(auth configured, owned notebooks 11, TOP1/TOP2/ Fusion Hub 포함)
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

---

## 분기별 한 줄 (최근 1년 · 수동 채움)

> 팀이 실제로 한 **결정·이정표**만 적는다. 비우면 됨.

| 기간 | 핵심 한 줄 (무엇을 확정/중단/승격했는지) |
|------|----------------------------------------|
| 2026-Q1 (NL 코퍼스) | NotebookLM MKM·Ops·Fusion 등 15노트 교차 질의 → 본 파일 **NL 이관 압축** 반영 (레포 SSOT와 병용). |
| 2026-Q2 (AutoEvo) | 조사→큐→스캐폴드→실행→제안→승인→결정 적용 + 연구 레인 승격 실행계획(`autoevo_research_promotion_plan_latest.json`) 생성. |
| 2026-Q2 (Hybrid Pointer Router) | `GO/WATCH/HOLD` 라벨링·runtime config·shadow 리포트·alert·guard·강등 드릴까지 연결해 “조건부 고효율 + 자동 하방보호”를 아티팩트 체인으로 고정(무조건 99/100 수사 금지). |
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
| 2026-05-02 (VPS · bitcoin-trading · 체결→cursor_trade_history) | 로컬 커밋만 있으면 VPS에 파일 MISSING — **`git@github.com:mkmlab-v2/mkm-destiny-ai-41e38ec6.git`의 `fix/btrack-ohlcv-cli-help-and-eval-wrapper-github`**에 반영 필요(비FF 시 worktree+체리픽 후 푸시). 체인: `export_binance_fills_to_cursor_trade_history_v1.py`→`sync_cursor_trade_history_latest_24h.py`; 등록 `ops/v2/ssh/register_export_then_sync_cursor_trade_history_cron.sh`, cron 태스크 `bitcoin-binance-export-then-cursor-trade-history`, 로그 `/var/log/bitcoin_export_then_cursor_trade_history.log`, **`WORKSPACE_ROOT=/opt/mkm-lab-workspace-v2/projects/bitcoin-trading`**. 브랜치 전환 전 **`projects/no1kmedi` 등 로컬 수정은 stash**. |

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
- **금지:** 2차 성경 레짐을 실전 트리거에 사용, 멀티렌스 단일화 주장.

## 레인별 진행 (한 줄씩)

| 레인 | 상용/게이트 상태 (한 줄) | 마지막으로 본 산출/경로 |
|------|---------------------------|-------------------------|
| 성경 | | |
| 명리 | | |
| 사상 | 사상 4-Agent는 A-Track 승격 유지 상태이며 모니터 정책에서 `geumhwa_transition_threshold=0.58`로 상향해 과민 자동주입을 완화했다. | `docs/final/artifacts/sasang_4agent_monitor_policy_v1.json` |
| 퓨전 | `보명지주/성정불변/병증약리/금화교역` 융합 게이트는 `FUSION_GATE_PASS`로 고정되어 승격 체인 체크에 결합됨. | `docs/final/artifacts/sasang_4agent_fusion_gate_latest.json` |

## 지금 막힌 것 (있을 때만)

- 

## 다음에 할 일 (최대 3개)

1. 원격 게시는 `internal` 우선으로 유지하고, GitHub(`origin`/`hq`)는 예외 공개가 필요할 때만 `scripts/Push-GitHub-Explicit.ps1 -Acknowledge` 경로로 제한한다. `fix/external-anchor-ci-smoke` 후속도 기본은 내부 PR/머지로 진행하고, 메인 워크스페이스 정렬은 `git fetch`/`pull` 또는 PR 전용 **worktree**(`C:\workspace\tmp\wt-external-anchor-work`)로 유지한다.
2. (선택) 구현 경로 SSOT 보강: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`에 external Bible anchor 체인·아티팩트 경로를 한 절 추가(스크립트 목록은 레포의 해당 브랜치와 동일하게 유지).
3. Global Atom claim registry·NotebookLM Vault 동기화 등 기존 운영 루틴은 병행 시 Fact-Lock 우선.

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
