# Research open questions — 심사·토의 큐 (v1)

**역할:** 레포 안에서 **아직 확정·승격 전**인 주제만 모은다. 여기 한 줄이 **구현 완료·테스트 통과·본선 반영**을 뜻하지 않는다. Fact-Lock·경로·게이트는 항상 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`와 호출 가능 스크립트가 우선이다.

**승격 루틴:** 토의로 결론이 나면 (1) `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 또는 `CONSTITUTION` 표·절, (2) 이슈/PR, (3) 스크립트·테스트 중 **해당하는 곳**으로 옮기고, 아래 표에서 **상태를 `CLOSED`로 바꾸거나 행을 삭제**한다.

**상태 태그:** `OPEN` = 심사 중 · `HOLD` = 정보 부족 · `CLOSED` = 이관 완료(행 유지 시에만)

---

## 큐 (표)

| id | 상태 | 주제 (한 줄) | 왜 열려 있는가 | 근거 포인터 (레포 경로만) | 다음 토의 질문 (한 줄) |
|----|------|--------------|----------------|---------------------------|-------------------------|
| RQ-001 | OPEN | B-track → Track A 승격 시 **latency·error 게이트 AND**를 운영에서 어떻게 증명할지 | AGENTS·플레이북에 수치 게이트가 있으나 현장 증빙 루틴이 사람마다 다를 수 있음 | `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9 · 루트 `AGENTS.md` A/B 승격 절 | 자동화 산출물 하나로 GO를 찍을지, 분기별 수동 승인을 남길지 |
| RQ-002 | OPEN | **NotebookLM MCP** `add_source` 실패(한국어 UI 등) 시 “웹 수동 업로드” 의존도를 얼마나 허용할지 | CENTRAL에 이미 한계가 기록됨; 재발 시 운영 부담 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` nl_sync · `docs/NotebookLM_sources_manifest.md` | MCP 패치 우선 vs Vault·웹만 SSOT로 고정할지 |
| RQ-003 | OPEN | **한의** 라벨 코호트 A vs 원전·Proxy B — 자동 파이프라인 경계를 어디까지 코드로 강제할지 | 핸드오프는 명시; 자동 합선 방지를 게이트로 더 쪼갤지 여부는 제품 정책 | `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` | B를 어떤 단계에서 차단하면 UX·연구 속도가 깨지지 않는지 |
| RQ-004 | OPEN | **국방 `GO_RESEARCH`** 레인과 Track C·상용 API 승격의 **이름·문서 상 분리**를 더 촘촘히 할지 | P0 표에 경로 있음; 대외 카피와의 거리는 정책 | `docs/final/P0_COMMERCIALIZATION_TRACKER.md`(국방 행) · `docs/final/artifacts/defense_code_pack_v1.json` | `research_only` 라벨을 어디(리포트·UI·패키지)까지 강제할지 |
| RQ-005 | OPEN | **MKM-Orchestrator** GO+·번인·글로벌 오케스트레이터 산출을 “운영 대시보드”에 얼마나 노출할지 | §1.4 표가 넓음; 노출 범위는 제품·보안 선택 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.4 | 운영자가 봐야 하는 최소 필드 집합은 무엇인지 |
| RQ-006 | OPEN | **Multi-Lens 중간 레이어** 잔여 행(번들 기본 밖)을 주차 단위로 밀 때 **우선순위 키**를 무엇으로 둘지 | 워크리스트에 “번들 DESCRIPTION이 SSOT”라고 이미 있음 | `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 하단 단일 태그 표 | TruthfulQA·Track A 하네스·BGM 중 다음 분기 하나만 고른다면 |
| RQ-007 | OPEN | **압축 투트랙** 마케팅·대외 문구와 `*_latest` 아티팩트의 **동기화 책임** (누가 언제 갱신하는지) | SLA·정책 문서는 있음; **2026-05-16** DRAFT 1-Pager 동결 — 법무·PUBLIC_FACING 전 검토 전 | `docs/final/COMPRESSION_SLA_POLICY_V1.md` · `docs/final/artifacts/compression_enterprise_executive_summary_v1.md` · `TRACK_C` §3.1.1 · `docs/final/P0_COMMERCIALIZATION_TRACKER.md` | 벤치 갱신 시 1-Pager 수치·면책을 누가 재동기화할지(주간 거버넌스 vs 릴리즈 태그) |
| RQ-008 | OPEN | **옵시디언 UNIVERSE** 그래프와 Git SSOT의 **이중 관리**를 줄일지 (인박스만 Git, 그래프는 로컬 유지 등) | CENTRAL에 볼트 격벽 이미 있음 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 옵시디언 절 · 로컬 `memory/obsidian_vault/UNIVERSE_MKm/` | 주 1회 동기화 의식으로 충분한지, 끌어올릴 노트 화이트리스트가 필요한지 |
| RQ-009 | OPEN | **실버 테크(시니어 음성·돌봄 UX)** 에 MKM **격벽·조율 상태·Fact-Lock** 패턴을 이식할 때 제품 경계·규제(B2G/B2B2C·보호자 동의·비의료 면책)를 어디까지 SSOT에 동결할지 | **2026-05-15 지휘관 승인:** `TRACK_C` §3.7.2 **(B)** 민감 외부 액션에 **구조적 휴먼 게이트**(자동 단독 실행 불가 전제, 알림·승인·차단·감사 로그) **SSOT 동결**. **파일럿 KPI 수치·마진·최종 면책 문구**는 Git SSOT 본문·동 §3 체크리스트에 **동결 지연** — 내부 R&D·제안 별첨·`silver_tech_cogs_unit_economics_template_v1.md` 등 `[HYPO]`. **(D)** 면책 초안·관할별 문구는 **법무 확정 후** 최종 반영. **2026-05-16:** 내부 면책·경계 **확장 초안 패킷** `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` 추가(대외 최종 아님). | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2 · `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3 **(v1.5)** · `docs/final/schemas/patient_care_bundle_v1.schema.json` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9 표(`patient_care_bundle_v1`) · `scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1` · `docs/research/silver_tech_cogs_unit_economics_template_v1.md` · `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` | **아래 `RQ-009 — CLOSED 이관 준비` 표 4행 전부** 충족·승격 위치 합의 후에만 `CLOSED`; 그 전까지 **`OPEN` 유지** |
| RQ-010 | OPEN | **초개인화 에이전트 / B2B 컨텍스트 API**(구조화 MKM·렌즈 프로필 JSON을 타사 앱·에이전트에 공급) 비전을 **IR·제안서 한 줄**로 열어두되, **제품·데이터·규제 SSOT**와 어떻게 분리할지 | 내부 운영(핸드오프·CONSTITUTION)과 **외부 결합**은 동의·TOS·데이터 최소화·의료·지식재산 경계가 다름; 명리·사상·Logos는 **렌즈 계약·격벽** 유지, 임상·실거래·본선 자동 합선 금지 전제와 정합 필요 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.3·§9 · `docs/final/P0_COMMERCIALIZATION_TRACKER.md` · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` · RQ-009 행 | 1차 파일럿 세그먼트(웰니스 코칭 vs 개발자 도구)·**사용자 동의·감사 로그**를 어디에 고정할지; LoRA 대량 개인화 vs **API+동적 컨텍스트** 운영 한도선은 어디로 둘지 |
| RQ-011 | OPEN | **미래 GTM: MKM 메타-뉴스**(사건 인제스트 Field → 사상·명리·Logos 렌즈 → Conflict/Final 인사이트; “편향 없음” 대신 **투명한 좌표계·감사 JSON** 선언) | 대량 뉴스×LLM은 **COGS·토큰 폭발**; **Phase 3(스케일업)** 전 본선 스위치 금지 가정과 정합. 구현·경로는 미확정 — 연구·GTM 가설만 큐에 봉인 | 루트 `AGENTS.md` 렌즈·Field→Lens→Final 출력 고정 · `docs/final/CENTRAL_AGENT_MEMORY_V1.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.1·§3.3(Logos 보조·실전 트리거 격벽) · `docs/final/artifacts/fixtures/mkm_meta_news_pipeline_stub_v1.example.json` · `tests/test_mkm_meta_news_pipeline_stub_v1.py` · RQ-010 행 | 1차 MVP는 **엔터프라이즈 인지 보조** vs **소비자 메타-뉴스** 중 어디인지; 인제스트·랭킹·로컬/하이브리드 라우팅·감사 스키마를 **어느 PR/절**로 이관할 타이밍인지 |
| RQ-012 | OPEN | **n8n 의존 축소**: Fact-Lock·감사를 위해 **판정·LOCK/UNLOCK·리스크 프로필 갱신**을 Git 버전 스크립트로 통일하고, n8n은 **원시 수집(Dumb Fetcher)** 이하로 둘지 **완전 제거**할지 | **2026-05-15:** Fact-Safe 체인·호출부 기본을 `--repo-source`(`repo.fact_safe_sync.v1`/`repo_shadow`)로 전환; `constitution_gates_v1.json` allowlist에 `repo.*`·레거시 `n8n.*`·`fact_safe_prophecy.*`+`shadow` 병행. 잔여: `MKM-n8n-Service`·매크로 일일 점검·쇼룸 ingest 스펙 등 **n8n 인프라** 철거 여부 | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§13.1.b** · `projects/bitcoin-trading/ops/windows-rehearsal/constitution_gates_v1.json` · `scripts/sync_fact_safe_risk_profile.py`(`--repo-source`·`--n8n-source`·`--allow-metadata-downgrade`) · `tests/test_sync_fact_safe_risk_profile.py` · `scripts/Run-FactSafeRiskProfileSyncChain_v1.ps1`(`-UseN8nSource`) · `scripts/Register-FactSafeRiskProfileSyncTask.ps1`(`-UseN8nSourceInTask`) · `scripts/Run-MacroRiskN8nDailyCheck.ps1` · `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.3·§13.1 · `AGENTS.md` 리스크 소스 절 · `JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` · `Register-N8nPersistentServiceTask.ps1` / `Run-N8nServiceGuardV1.ps1` | **잔여 3단계:** (1) 운영 PC에서 `\MKM-FactSafe-RiskProfile-Sync-4H`를 `-Force`로 재등록해 새 러너 기본값 적용 여부 확인 (2) n8n 일일 점검·서비스 태스크 필요성 재평가 (3) 쇼룸 ingest를 로컬 스크립트 단일 SSOT로 옮길지 |
| RQ-013 | OPEN | **Safety-critical 실행 거버넌스 → 자율주행 “주행 NN 밖 감시 레이어”** 확장 가설 — **상용·차량 스택 개발 추진 아님**; IR·클로징 **10% 비전**만 허용 | **2026-05-15 지휘관:** LG 발표 종료·결과 대기. 방향(OEM 책임·불확실 시 HOLD/MRM)은 `[HYPO]`로 유지; **주행 인식 향상·ISO 26262/SOTIF 충족·사고율 0%·장-뇌 은유=차량 물리 팩트** 대외 단정 **금지**. 본선은 가전 제어 무결성 PoC; 자율주행 코드·인증 산출물 **레포에 없음** | `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.2.1(`mkm_control_integrity_*`) · §3.8.3(`fusion_control_integrity_audit`) · §28(`athena_run_v1`) · `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.11 · `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` §3(v1.7 은유·금지 예시) · 루트 `AGENTS.md`(장-뇌·홍보 프레이밍·발표 70/20/10) · `docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md` | **아래 `RQ-013 — CLOSED 이관 준비` 표 4행 전부** 충족 전 **`OPEN` 유지**; LG(또는 1차 OEM) PoC **결과 후**에만 “센서 불일치→WATCH/HOLD→MRM” 파일럿 범위를 **어느 PR/절**로 이관할지 토의 |
| RQ-014 | OPEN | **B-track 예언 — ensemble v1(명리+사상 평균) vs v2(신뢰도 가중·렌즈 분리) ablation** 및 **승격 WF 신호 정렬** | **2026-05-15:** `rule_based_ensemble_v1`이 `myeongni_sasang` 평균·고정 가중 합; strict WF **0.55** 미달(렌즈 ~0.486, instrument ~0.535). 신규 도메인보다 **배선·ablation** 우선 | `scripts/generate_btrack_hypothesis_prophecy_v1.py`(`rules.ensemble_mode=v2_confidence_fusion`) · `docs/final/artifacts/btrack_lens_ensemble_v1.json` · `scripts/run_btrack_ensemble_fusion_ablation_v1.py` → `reports/btrack_ensemble_fusion_ablation_v1_latest.json` · `scripts/eval_prophecy_promotion_gates_v1.py` · `reports/prophecy_promotion_gates_recommended_chain_v1_latest.json` | v2 ablation이 v1 대비 OHLCV hit-rate를 올리면 `ensemble_mode` 기본 전환 여부; **WF 0.55** 통과 전 A-track·실매매 합선 금지 |
| RQ-015 | OPEN | **Logos Track B** 학술 연구(주석 계통 비교·사본학·2차 문헌 스택 등)를 **Phase N(현 슬라이스 밖)**으로 두고, 증축은 **구절 코퍼스·증류·`[NON_GATING]`** 경계 안에서만 할지 | 백로그 축(원어·교차참조·문헌 맥락)과 실구현 슬라이스 사이에 “학술 성경학 전부” 과대 스코프가 비어 있음; 격벽·법무·대외 신뢰를 명시 동결하려면 범위 한 줄이 필요 | `docs/final/LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`(Logos Track B 표) · `docs/final/CENTRAL_AGENT_MEMORY_V1.md`(NL 1목적=1노트북) · **메타포 DB v0.2.1:** `docs/research/logos_metaphor_db_v1/theme_01`–`05` · `docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json` · `scripts/build_logos_research_card_v1.py` · `tests/test_build_logos_research_card_v1.py` · **쇼룸 스냅샷:** `scripts/build_showroom_logos_research_slice_v1.py` · `public_showroom_logos_research_v1.html` · `tests/test_build_showroom_logos_research_slice_v1.py` | Phase N에 넣을 **최소 MVS**(데이터·HITL·라이선스)와 **`CONSTITUTION`/백로그 이관 시점**을 언제로 둘지 |
| RQ-016 | OPEN | **압축 Meta-Policy** — 도메인 유입 시 lexicon·shard 자동 정렬(수동 핀포인트 축소) | 2026-05-16 sweep: **scm/health selective bridge** → scm Jaccard **1.0** 가능하나 **global saving < 0.47**; soft-term 핀도 동일 tradeoff → **baseline 유지** | `compression_domain_bridge_sweep_v1_latest.json` · `compression_scm_shard_pin_experimental_v1.json` · `run_compression_domain_bridge_sweep_v1.py` | Per-domain **cap tuning** 또는 literal 프로필 분기; Track A opt-in은 floor 통과 실험 후 |
| RQ-017 | OPEN | **토큰 절감 ↔ 보드 실측 지연(ms)** 상관 — edge/NPU 하드웨어에서 입증 | **2026-05-16:** 로컬 페이로드 스윕 + **VPS triplet OK** (p95 median **~710ms**); **인과 주장 금지** | `compression_board_ms_vps_bench_triplet_v1_latest.json` · `Run-CompressionBoardMsVpsBenchTriplet_v1.ps1` · `compression_board_ms_correlation_report_v1_latest.json` | edge/NPU·페이로드–절감 A/B; LG **C-S3 2026-05-20**; OEM ms **휴먼** |
| RQ-018 | OPEN | **Shadow Auditor** — 야간 `test_ultra_compression_artifacts` + loss-pattern → research 큐 자동 적재 | **2026-05-16 구현:** `run_compression_shadow_auditor_v1.py` · 일일 `Register-CompressionShadowAuditorDailyTask.ps1` · 주간 `-IncludeShadowAuditor` | `scripts/run_compression_shadow_auditor_v1.py` · `reports/constitution/btrack_pilot/compression_shadow_auditor_latest.json` · `compression_research_metaphor_debug_queue.jsonl` · `tests/test_run_compression_shadow_auditor_v1.py` | 웹훅·Track A 자동 승격 연결 여부; board ms(RQ-017) 상관 리포트 병합 |
| RQ-019 | OPEN | **MKM Inter-Agent Encoding** (「MKM Language」/ Lingua Franca `[VISION]`) — SOTA 4축(시맨틱·신경압축·슈퍼토큰·프롬프트 경제)과 **레포 층** 정렬·승격 조건 | **2026-05-19:** `core_ready` + **live HTTP curl** 박제 · CI `inter-agent-encoding-smoke.yml` · IR 스니펫 `mkm_inter_agent_ir_snippet_v1.md` · 법무 전 대외 **미승격** | `mkm_inter_agent_encoding_status_latest.json` · `mkm_inter_agent_first_message_live_http_v1.json` · `Invoke-MkmInterAgentEncodingSmoke_v1.ps1` | **CLOSED** = 법무 Sign-off + PUBLIC_FACING 이관; 기술·curl 증거는 **완료** |

### RQ-019 — `CLOSED` 이관 준비 (체크리스트 · **M1–M3·법무 전까지 `OPEN` 유지**)

아래 **전부** 충족·지휘관 합의 후: (a) RQ-019 **`CLOSED`**, (b) 대외 한 줄을 `TRACK_C` / `PUBLIC_FACING` / P0 중 **합의된 절**로만 이관. **부분 충족으로 `CLOSED` 금지.**

| # | 조건 | 근거·산출 |
|---|------|-----------|
| 1 | **M1** v2 Trust Packet **Phase 2** — expand = packet only, 재조립 라운드트립 | **`[FACT]`** pytest 17+3 · in-process + **live HTTP** `mkm_inter_agent_first_message_live_http_v1.json` |
| 2 | **M2** Inter-agent **wire profile v0** + 통합 status 리포트 | **`[FACT]`** `mkm_inter_agent_wire_profile_v0.json` · `mkm_inter_agent_encoding_status_latest.json` |
| 3 | **M3** Human decoder **게이트·한계** 대외 허용 문장 확정 | `l1_inverse_decoder_spike_test_summary_latest.json` · `PUBLIC_FACING` |
| 4 | 대외 카피 **법무** — Lingua Franca 완성·토큰 0·100% 복원·4D 운영 와이어·학계 SOTA 우위 **없음** | `mkm_inter_agent_encoding_sota_map_v1.md` Kill-Matrix |

### RQ-009 — `CLOSED` 이관 준비 (체크리스트 · **법무·실측 전까지 `OPEN` 유지**)

아래 **전부**를 만족하고 지휘관·법무가 **승격 위치**를 합의한 뒤에만: (a) 위 표에서 RQ-009를 **`CLOSED`**로 바꾸고, (b) 확정 문구·수치를 `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` / `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` 등 **최종 SSOT**에 반영한다. **부분 충족으로 `CLOSED` 금지.**

| # | 조건 | 근거·산출 |
|---|------|-----------|
| 1 | **(D)** 관할·채널별 **최종** 면책·경계 문구 법무 서면(또는 등가 승인 로그) | `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` 초안을 **교체**할 확정본 존재 |
| 2 | 파일럿 KPI **수치**·마진·COGS **월소계**가 `[HYPO]`가 아닌 **의도된 SSOT 파일**에 들어갈지 합의(별첨만 유지할지 포함) | `docs/research/silver_tech_cogs_unit_economics_template_v1.md` **S-CONS/BASE/STRESS 실측** 절 + 벤더 청구/콘솔 메타 |
| 3 | STT·감사 카피와 모순 없음 | `stt_routing_audit_log_v1` · `PUBLIC` §3 GTM/Trust 불릿 |
| 4 | **(B)** 민감 외부 액션 구조적 휴먼 게이트가 **제품 플로우 문서**와 한 줄로 정렬됨 | `TRACK_C` §3.7.2 `(B)` |

### RQ-013 — `CLOSED` 이관 준비 (체크리스트 · **PoC·OEM·실측 전까지 `OPEN` 유지**)

아래 **전부**를 만족하고 지휘관이 **승격 위치**를 합의한 뒤에만: (a) 위 표에서 RQ-013을 **`CLOSED`**로 바꾸고, (b) 확정 범위·대외 한 줄을 `TRACK_C` / `PUBLIC_FACING` / `CONSTITUTION` 등 **해당 절**로만 이관한다. **부분 충족으로 `CLOSED` 금지.** 본 큐 단계에서 **차량용 스크립트·ISO 인증 문구·0% 수치**를 SSOT 본문에 넣지 않는다.

| # | 조건 | 근거·산출 |
|---|------|-----------|
| 1 | 1차 **가전/OEM PoC** 결과·과제 범위 확정(합격·탈락·추가 질문 포함) | LG 모두의 챌린지 등 **지휘관 확정 로그**; `lg_hs_*` 발표 자료는 범위 참고만 |
| 2 | **두 번째 수직** 또는 OEM **LOI/파일럿 계약** 포인터(문서·계약 경로; 수치·대외 약속은 별도 Fact-Lock) | `TRACK_C` §3.11 (2) 밸류에이션 조건 |
| 3 | 차량·안전 도메인 **골든셋·실측·게이트** 경로가 `CONSTITUTION` 표에 등록·pytest·exit code로 재현 가능 | 신규 스크립트는 **B-track·`research_only`** 태그; A-track·실매매 자동 합선 없음 |
| 4 | 대외 카피 **법무·PUBLIC §3** — ISO 26262/SOTIF **“충족/인증”**, 사고율 **0%**, 장-뇌·호르몬 **입증** 문구 없음 | `PUBLIC_FACING` v1.7 · `TRACK_C` §3.5–3.6 부록 |

## IR·제안서 한 줄 초안 ([HYPO] · RQ-010)

대외 최종 아님. 법무·동의 UX·제품 경계 확정 후 `docs/final/P0_COMMERCIALIZATION_TRACKER.md` / `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` / `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`로만 승격.

- **KO:** 동의·감사·데이터 최소화 전제의 MKM 구조화 프로필 API로, 파트너 AI가 사용자 톤·우선순위를 잃지 않게 돕습니다. (의료 진단·투자·실거래 신호 아님.)
- **EN:** With consent, auditability, and data minimization, MKM’s structured profile API helps partner AIs stay aligned to each user’s tone and priorities—without claiming medical diagnosis, investment advice, or live trading signals.

### 메타-뉴스 스파이크 ([HYPO] · RQ-011)

**구현·API·크롤 없음.** Field→Lens→Final **JSON 형태**만 레포에 고정한다. 대량 인제스트·LLM 라우팅은 Phase 3·COGS 설계 후 `CONSTITUTION`/스크립트로 이관할 때 `CLOSED` 처리.

- **픽스처:** `docs/final/artifacts/fixtures/mkm_meta_news_pipeline_stub_v1.example.json` — `hypothesis_tier: B`, `boundary_ack`, `lenses.logos.role: NON_GATING`, `audit.weights`·`model_route`·`evidence_path`.
- **인제스트 후보(라이선스·ToS·저작권 선행):** 상용 뉴스 API, 파트너 전용 피드, 공개 RSS(약관 검토) 등 — **코드 연결 금지**까지는 아니나 본 큐에서는 후보명만 유지.
- **감사 JSON 최소 필드(초안):** `field.id`/`published_at`, 렌즈별 `confidence_level`, **Logos `NON_GATING`**, `audit.weights`, `model_route`, `evidence_path`, `validated_at`(로컬 ISO), `boundary_ack`.
- **회귀:** `tests/test_mkm_meta_news_pipeline_stub_v1.py` — 픽스처 키·Logos 역할만 검증(스키마 jsonschema 단계는 승격 시).

### 자율주행 safety governor — IR 클로징 한 줄 ([HYPO] · RQ-013)

**구현·차량 스택·인증 없음.** 대외 최종·과제 제안 본문이 아님. LG 등 **1차 PoC 결과 후** Q&A·후속 미팅에서만 사용; `TRACK_C` / `PUBLIC_FACING` 승격 전 **[HYPO]** 유지.

- **KO:** 우리가 증명하는 것은 더 똑똑한 주행 AI가 아니라, **불확실할 때 실행을 멈추는 운영·검증 레이어**입니다. 가전 PoC에서 검증한 동일 디시플린을, **별도 실측·규제 트랙**에서 안전이 치명적인 물리 시스템으로 단계 확장할 수 있습니다 — **자율주행 상용 약속은 PoC 통과 후**입니다.
- **EN:** We do not sell smarter perception; we sell an **auditable governance layer** that defers execution when uncertainty rises. The same discipline validated in appliance PoC may extend to other safety-critical systems **only after separate measurement and regulatory tracks** — not as a current product commitment.

**금지 (대외):** “ISO 26262 certified,” “0.00% collision,” neuroscience-proven safety, gut–brain metaphor as vehicle physics.

### Inter-agent encoding — IR 클로징 한 줄 ([HYPO] · RQ-019)

**구현·표준·프로덕션 SLA 없음.** `mkm_inter_agent_encoding_sota_map_v1.md` §5와 동일. Whitepaper·투자 본문 **승격 전** `[HYPO]` 유지.

- **KO:** LLM 간 통신 비용·지연 문제에, MKM은 **측정된 렉시콘·도메인 통제 압축**과 **Trust Packet 초안**으로 에이전트 인코딩 레이어를 쌓는 중입니다. 무손실 공통어·SLA 완성은 **주장하지 않습니다**.
- **EN:** MKM is building a measured lexicon rail and governed compression baseline under a Trust Packet draft toward inter-agent encoding—not a finished lingua franca or production SLA.

**금지 (대외):** “MKM Language shipped,” “token cost zero,” “100% lossless decode,” “semantic embedding wire in production,” “beats SOTA papers.”

---

## 메타

- **schema:** `research_open_questions_v1`
- **last_reviewed_utc:** 2026-05-19 — **RQ-019** 추가(MKM Inter-Agent Encoding / SOTA 4축 맵·M1–M3 승격 체크리스트). (이전: 2026-05-16 RQ-015 Logos Phase N 등.)
- **mirror (optional):** 로컬 그래프용 `memory/obsidian_vault/UNIVERSE_MKm/INBOX_연구_토의큐.md` — Git과 자동 동기화하지 않는다.
