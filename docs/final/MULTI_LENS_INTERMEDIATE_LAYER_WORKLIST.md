# 중간 레이어 다중 렌즈 — 작업 리스트 (B-track 정합)

**작성일**: 2026-03-30  
**상위 SSOT**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (Multi-Lens·격벽·TOE 비단정)  
**목적**: 단일 “통합장 완성”이 아니라, **렌즈별 격벽을 유지한 채** 아티팩트·테스트·문서·CI가 **같은 사실**을 가리키게 만드는 **중간 레이어** 정합 절차를 정리한다.

---

## 완료 정의 (이 문서의 “끝”)

- **여기서 끝**: B-track 벤치·가설·관측이 **저장소 경로·pytest·CI**로 재현 가능하고, **실매매·OOF·A-track 자동 합선**이 없다.
- **여기서 끝 아님**: 상용 승격, 처방 엔진 합선, 단일 수학적 TOE 선언 — **Promotion Loop·별도 PR** 영역.

---

## Phase 1 — CROSS_REF (정경 ↔ 위성 ↔ `state_id`)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 1.1 | `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` 행 수·`canonical_ref` ↔ `LOGOS_STATE_MAPPING_V1` | [x] | 회귀: `tests/test_cross_ref_dss_schema.py` |
| 1.2 | `docs/final/CROSS_REF_DRAFT_V2_DOCUMENT.schema.json` + jsonschema 검증 | [x] | 동일 테스트 내 `test_cross_ref_draft_validates_against_json_schema` |
| 1.3 | `docs/final/btrack_phase3_cross_ref_snapshot.md` — SSOT와 동일 ENTRY·코드펜스 | [x] | 백틱·`disclaimer` 많을 때 **닫는 펜스**만으로 자르지 말 것 |
| 1.4 | 대규모 수정 시: **JSON을 SSOT로 편집 → 스냅샷 펜스 갱신** | [x] | `py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply` 후 `pytest tests/test_cross_ref_dss_schema.py` |

---

## Phase 2 — 사상·명리 벤치 (Timing / Vessel)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 2.1 | `docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json` + 청크 테이블 조인 | [x] | `tests/test_sasang_cross_ref_draft.py` |
| 2.2 | `data/myeongni/insight_observation_log*.jsonl` + `MYEONGNI_FUSION_INTERFACE_STUB.json` | [x] | `tests/test_myeongni_insight_observation_log.py` (파일 추적은 팀 정책) |
| 2.3 | `docs/final/MYEONGRI_INSIGHT_SSOT.md` — §1.2 대운·세운 테이블 표 | [x] | 확정 경로는 표 첫 행에 추후 기입; 미확정은 `—`·`[HYPO]` |

---

## Phase 3 — CI · 로컬 번들 (Fact-Lock)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 3.1 | `.github/workflows/dual-regime-integrity.yml` — dual-regime + workspace + myeongni 순서 | [x] | `integrity_guard` 포함 |
| 3.2 | `run_prophecy_alignment_pytest.ps1` / `.sh` — **CI 워크스페이스 테스트와 동일 목록** | [x] | logos + CROSS_REF + ENTRY16 source-hunt(log+summary) + SASANG + myeongni insight + 4-grid myeongri·sasang compression spike |

---

## Phase 4 — 운영 · Promotion 경계

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 4.1 | B-track `note`·`[HYPO]` — ENTRY_11 패턴 유지 | [x] | `CROSS_REF`·NL 반증 박제 |
| 4.2 | A-track·실매매·트레이딩 로더 — **본 경로 기본 로드 금지** (CONSTITUTION §4·§8) | [x] | 정책 문서; 승격 시 PR |
| 4.3 | NotebookLM / vault — **중복 소스 제거**, `docs/NotebookLM_sources_manifest.md` 준수 | [x] | `-WhatIf` 점검: 중복 0건 (2026-03-30). **2026-05-14:** 노트북 **레포 인덱스** — `RESEARCH_HISTORY_V1.md`=MCP **현행**만; 41개 과거=`docs/final/artifacts/research_history_notebooklm_snapshot_2026-04-12.md`; Vault sync·OPS 렌즈 팩에 현행 인덱스 반영. |
| 4.4 | `ENTRY_07/08/16` 외부 판본 대기 큐 운영 전환 | [x] | `docs/final/CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_2026-03-30.md`의 "외부 판본 대기 큐" 섹션 참조 |
| 4.5 | 대기 큐 모니터링 주기 고정(월 1회/소스 공지 이벤트) | [x] | 대기 큐 재시도는 신규 근거 소스 등장 시에만 실행 |
| 4.6 | 월간 점검 명령 템플릿 고정 | [x] | 체크리스트에 Windows 실행 템플릿 추가 |
| 4.7 | 월간 점검 스크립트 옵션(`-SkipBundle`) 운용 규칙 명시 | [x] | 정기 점검=기본(번들 포함), 이벤트 직후 1차 확인=옵션 허용 |
| 4.8 | 월간 점검 실행 로그(JSONL) 누적 운영 | [x] | `docs/final/artifacts/waiting_queue_monthly_check_log.jsonl`에 skip/full 1회 이상 기록 |
| 4.9 | 월간 점검 후 ENTRY16 summary 계약 테스트 유지 | [x] | `tests/test_entry16_source_hunt_summary.py`로 출력 계약 고정 |
| 4.10 | ENTRY16 승격 게이트 리포트/계약 테스트 유지 (Direct + Proxy Manual 경로) | [x] | `scripts/evaluate_entry16_promotion_gate.py` + `tests/test_entry16_promotion_gate.py` |

**연구·정책 큐(Phase 4 밖):** Track C 실버 UX·면책·B2G 경계는 `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-009** (`OPEN`). `patient_care_bundle_v1`(CONSTITUTION §9)은 **엔지니어링** 템플릿·정책·MD·P0·`PUBLIC_FACING` §3 cross-check까지 배선. **2026-05-15 지휘관 승인:** 민감 외부 액션 **구조 Lock**은 Track C §3.7.2 `(B)`에 반영; **파일럿 KPI 수치·최종 면책**은 SSOT 동결 지연(`PUBLIC` v1.3). 잔여: 법무·실측 후 RQ-009 `CLOSED`/이관.

---

## Phase 5 — 선택 (자동화)

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 5.1 | `CROSS_REF` JSON → `btrack_phase3_cross_ref_snapshot.md` 코드펜스 덤프 | [x] | `scripts/sync_btrack_phase3_snapshot_json_fence.py` |
| 5.2 | `multi_corpus_policy` / 격벽 테스트 — 위성 코퍼스 추가 시 확장 | [x] | `tests/test_multi_corpus_isolation_policy.py`; 증거 수집표: `docs/final/CROSS_REF_CITATION_ANCHOR_EVIDENCE_CHECKLIST_2026-03-30.md` |

---

## 한 번에 돌리는 명령 (Windows)

저장소 루트에서:

```powershell
# 단계 순서·4b(Premium multilens) 등은 `scripts/run_fact_lock_bundle.ps1` 상단 `.DESCRIPTION` 주석이 SSOT(아래 한 줄은 진입점만).
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_fact_lock_bundle.ps1
```

**통합 거버넌스 v1:** `run_fact_lock_bundle.ps1` 말미(Safe ops 전)에 `scripts/invoke_build_integrated_governance_if_deps_present_v1.py`가 기본 실행된다(KOSPI 게이트·`integrated_governance_config_v1.json`이 모두 있을 때만 실제 빌드·`--validate-digest-schema`; 없으면 SKIP exit 0). 생략: `-SkipIntegratedGovernanceBuild`. 동일 invoker는 `Invoke-TrackCMacroDailyFusion_v1.ps1`(ops 대시보드 직전)·`Invoke-MkmAiV2DailyReadiness.ps1`에도 연결된다.

번들만(스모크+Fact-Lock, integrity 생략 시 `-SkipIntegrityGuard`):  
`Set-Location C:\workspace\projects\bitcoin-trading` 후 `.\ops\v2\tasks\run_prophecy_alignment_pytest.ps1`.

`dual-regime-integrity`와 동일한 워크스페이스 테스트를 포함하려면 위 스크립트가 **최신**인지 확인한다 (`CONSTITUTION` §6 표·**CI tail 포인터 행** + `.github/workflows/dual-regime-integrity.yml` 순서 SSOT). **`_pr_sasang_promotion` 미러**를 루트와 맞출 때는 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Sync-PrSasangPromotionMirror_v1.ps1`(루트 `AGENTS.md` 등 고정 목록 복사; P0 경로에 스크립트 포함). 선택: `run_workspace_automation_health.ps1 -IncludePrSasangPromotionMirrorSync` 또는 `-PrSasangPromotionMirrorSyncOnly`.

사상–사주 조인트 문헌·큐레이트 파이프라인(Europe PMC 픽스처·오프라인 회귀 7 + **승인 출처** `data/myeongni/curated_saju_joint_v1.jsonl` 인제스트 1)은 `run_fact_lock_bundle.ps1` **기본**에 포함된다. 생략: **로컬 번들만** `-SkipSasangSajuJointLiteraturePipeline`(GitHub `dual-regime-integrity.yml` CI 단계에는 해당 스킵 플래그 없음·전체 회귀 고정). **끝단 staleness(선택 생략):** `-SkipCuratedJointStalenessCheck` — 큐레이트 시각(`ingest_at_utc`·행 없으면 파일 mtime) vs `docs/final/artifacts/myeongni_celebrity_hit_rate_v1.json` `generated_at_utc` 24h 초과 시 `STALE` 기록 · `scripts/check_curated_saju_joint_staleness_v1.py`·`reports/curated_saju_joint_staleness_v1_latest.json`. 스크립트·데이터·pytest는 `CONSTITUTION` 표 **「사상체질↔문헌↔사주 조인트」**·동 워크플로를 본다.

MKM Control-Integrity Golden/LoRA 파이프라인 스모크(`tests/test_mkm_control_integrity_pipeline_smoke_v1.py`)는 `run_fact_lock_bundle.ps1` **기본**에 포함된다(번들 주석 5d). 로컬만 생략: `-SkipMkmControlIntegritySmoke`. SSOT: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §1.2.1.

**Athena CENTRAL 체크포인트·Two-track/Multi-symbol·Aramaic·Logos insight bundle v1:** `tests/test_athena_checkpoint.py` 직후 로컬 번들 전용 **3d2c**(`test_run_vertex_gemini_agent_search_context_v1.py`; Vertex Agent Search 명시적 RAG 헬퍼·오프라인; `-SkipVertexAgentSearchContextUnit`·GitHub `dual-regime-integrity.yml` 미포함)·**3d2d**(`test_athena_daily_thread_log_sync_v1.py`; 다중 채팅 일기 MD 병합·오프라인 — **Ops 한 줄·「일기 반영」**; 임무·MISSION·Phase 표 앵커는 루트 `MISSION_LOG.md`·`MISSION_LOG.template.md` 「채팅창 작업일정 앵커」와 역할 분리; `-SkipDailyThreadWorkLogUnit`)·이어 CI `dual-regime-integrity.yml`과 동일 **Two-track submission pack**(pytest 3)·**Multi-symbol gates**(pytest 3) — `scripts/run_fact_lock_bundle.ps1` 기본 **3d2a**(생략 `-SkipTwoTrackSubmissionAndMultiSymbolSmoke`)·이어 Aramaic 단계와 동일 **27**개 pytest(**3d2b**; 생략 `-SkipAramaicBtrackGraphPipelineSmoke`)·`tests/test_logos_insight_bundle_schema_v1.py`·`tests/test_build_logos_insight_bundle_v1.py`(**3d3**). CI Athena §28·Two-track·Multi-symbol·Aramaic·Logos 단계와 정합. **dual-regime PR paths:** Aramaic 블록에 Windows 일일 예약 래퍼 `scripts/Register-AramaicMvpDailyTask.ps1`·`scripts/Verify-AramaicMvpDailyTaskReadiness.ps1` 포함(Track T survivor dry-run 인자·readiness 출력 변경 시 CI 재실행). non-degraded 스키마 예: `docs/final/schemas/logos_insight_bundle_v1.non_degraded.example.json`, 재생성 `py scripts/materialize_logos_insight_bundle_non_degraded_example_v1.py`.

**GCS에 PDF만 올린 뒤 Agent Search가 비는 경우(ADC):** 데이터 스토어는 자동 완전 동기가 아닐 수 있으므로 `py scripts/bootstrap_agent_search_datastore_gcs_v1.py --project <id> --bucket <bucket> --gcs-prefix agent-search-docs/ --skip-create`(INCREMENTAL `ImportDocuments`) 후 검색·스모크를 돌린다. Windows 원클릭: `scripts/Run-VertexGeminiAgentSearchContextSmoke_v1.ps1 -ImportDocumentsFirst …`(래퍼가 동일 import를 선행).

**Track C macro fusion smoke (헬스 전용, 번들 밖):** `scripts/run_workspace_automation_health.ps1 -IncludeTrackCMacroFusionSmoke` 또는 `-TrackCMacroFusionSmokeOnly` — Invoke에 `-SkipGateAlert -SkipExodusSourceFetch` 고정. Logos `build_logos_insight_bundle_v1.py` 생략: **`-SkipLogosInsightBundle`** 또는 User/머신 **`MKM_HEALTH_FUSION_SKIP_LOGOS_INSIGHT_BUNDLE`** truthy. SSOT: `CONSTITUTION` §1.3.1 표.

Premium B-track multi-lens report v1(스키마 + `build_premium_btrack_multilens_report_v1` 서브프로세스 회귀 + `premium_multilens_job_queue_stub_v1` 큐 스텁 pytest)은 `run_fact_lock_bundle.ps1` **기본** 단계 4b(일일 실행 인사이트 브리프 pytest 직후)에 포함되며, **직후** `premium_multilens_job_queue_stub_v1.py drain --allow-missing-queue` 1회·**이어** `build_premium_multilens_queue_promotion_gate_v1.py --skip-pytest`(S1_SHADOW 승격 게이트 산출)가 이어진다. CI `dual-regime-integrity.yml` 동일. 선택 스냅샷: 동 스크립트 **`export-pending --out-json …`**. 일상 원클릭: **`scripts/Invoke-PremiumMultilensQueueRoutine_v1.ps1`**(`-ExportPendingJson` 선택; 기본 말단에 동 게이트 `--skip-pytest`, `-SkipPromotionGate`로 생략). SSOT: `CONSTITUTION` 표「Premium B-track multi-lens report v1」. 헬스 체인에서만 돌릴 때: `scripts/run_workspace_automation_health.ps1 -IncludePremiumBtrackMultilensReportSmoke`  
**시맨틱+RAG 번역 브리지 v1:** `tests/test_semantic_rag_bridge_insight_bundle_schema_v1.py`·`tests/test_build_semantic_rag_bridge_insight_bundle_v1.py`는 철학 RAG 파일럿 pytest 직후 **`run_fact_lock_bundle.ps1` 5c3**·CI `dual-regime-integrity.yml`(Premium gate 직후)에 포함된다. 빌더: `scripts/build_semantic_rag_bridge_insight_bundle_v1.py`.

B-track 세션 시각 명리 패널·날씨/OHLCV 조인·상관 회귀(4 pytest, CI `dual-regime-integrity` General prophecy 직후 단계와 동일)는 **`projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`**·`.sh` 워크스페이스 번들(번들 2단계)에 포함된다. `run_fact_lock_bundle.ps1`는 해당 스크립트를 선행 호출하므로 **중복 실행 없이** 동일 회귀가 돈다.

한의 의사 CDS assist envelope v1·자동화 레지스트리(회귀 4파일: CDS 3종 + `tests/test_automation_registry_json_v1.py`)은 `run_fact_lock_bundle.ps1` **기본** 단계 3e. 로컬만 생략: `-SkipKmPhysicianCdsEnvelope`. 빠른 점검: `scripts/run_workspace_automation_health.ps1 -IncludeKmPhysicianCdsEnvelopeSmoke` 또는 P0+해당 pytest만 `-KmPhysicianCdsEnvelopeSmokeOnly`. 배치 실행: `py scripts/run_km_physician_cds_assist_envelope_batch_v1.py --in tests/fixtures/km_physician_cds_assist_payload_batch_v1.example.jsonl --out reports/km_physician_cds_envelope_batch_latest.jsonl`.

등록한 Windows 주간 작업(`MKM-KmPhysician-CdsEnvelopeBatch-Weekly`, `MKM-BTrack-BtcWeight-HitRateBundle-Weekly`)은 `projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json` 기대 목록과 맞추고, 워크스페이스 헬스의 `reconcile_automation_registry.ps1` 단계로 drift를 본다.

---

## CI 잡(`dual-regime-integrity`) vs Fact-Lock 번들 격차 로드맵 [VISION]

**CI tail (Phase C 권장):** `MKM personal briefing guardrails` **다음** 스텝부터 job 끝까지의 **순서·묶음**은 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §6 **CI tail 포인터 행**과 `.github/workflows/dual-regime-integrity.yml`만 전개 SSOT로 둔다(§6 표에 tail 전 스텝을 1:1 나열하지 않음).

`scripts/run_fact_lock_bundle.ps1` 상단 `.DESCRIPTION`이 범위 SSOT다. 아래는 **1:1 동치를 목표로 하지 않는** 나머지를 주차 단위로 밀어붙일 때의 고정 분해다(날짜는 달력 아닌 **상대 순서**).

| Phase | 목표 주차(권장) | 범위 | 완료 정의 |
|-------|------------------|------|-----------|
| A | W0(완료) | `dual-regime-integrity`에 이미 포함된 Aramaic·Two-track·Multi-symbol pytest 블록 | CI 녹색 + CONSTITUTION 테스트 표·워크플로 행 정합 |
| B | W1(완료) | Windows Task Scheduler **등록/검증 스크립트**를 레포에 두고 P0 경로에 포함 | `Register-AramaicMvp*` / `Verify-AramaicMvp*` / `Run-AramaicMvp*WeeklyChain_v1.ps1` 존재 + `verify_p0_constitution_gate_paths.ps1` 통과 |
| C | W2–W3(진행·CONSTITUTION 비고·§6 서문·MULTI_LENS 단일 태그 표에 **서피스 태그** 반영) | **장시간·외부 비용** 후보를 CI·번들·헬스에 **단일 태그**로 고정(아래 표) | 표의 각 행이 SSOT 한 곳에만 기술되고 중복 주장 없음; **dual-regime job tail**은 §6 포인터 + 워크플로 YAML만 전개 |
| D | W4+(부분 완료) | `automation_registry.json`·표준 Task 이름 | Aramaic 3태스크 행 추가 + `tests/test_automation_registry_json_v1.py` `MKM_REQUIRED_NAMES` 정합; 미등록 호스트는 `optional: true`로 reconcile 녹색 |

**단일 태그 표 (Phase C 앵커):** 세부 경로·스위치는 `scripts/run_fact_lock_bundle.ps1` 상단 `.DESCRIPTION`·`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·`AGENTS.md`가 우선한다.

| 항목 | CI 포함 (`dual-regime-integrity`) | Fact-Lock 번들 기본 | 헬스/선택 전용 |
|------|-----------------------------------|----------------------|----------------|
| integrity_guard + prophecy alignment PS1 + 대부분 pytest 스택 | 예 | 예(동일 케이스 커버 목표) | — |
| TruthfulQA pytest·gate·repro·번들-gate 회귀 | **예**(CI TruthfulQA 단계) | `run_fact_lock_bundle` 기본은 생략; `-IncludeTruthfulQa*`로 정렬 | — |
| TruthfulQA MC/Generation 벤치 산출·eval 게이트 **본실행** | 아니오 | **번들 선택**(`-IncludeTruthfulQa*`) / `Run-TruthfulQAReproBundleV1.ps1` | 외부 비용·시간 상한 별도 |
| B-track·뉴스·Logos·Survivor·일반예언·세션·날씨120d·Lexicon·L1·토큰·압축·LoRA·Athena (`dual-regime`, TruthfulQA 직후 연속 스텝) | **예** | 번들과 부분 중복 | §6 표 복합 행·CI 순서 정렬 |
| MKM meta-layer envelope·Token API hydration trend (`dual-regime`, 렌즈 PoC 묶음 직후) | **예** | 생략 가능 | — |
| B-track 표면·Track C/Cross-lens RAG·프리미엄·브리핑 가드 (Token API hydration trend pytest 직후) | **예** | 생략 가능 | §6 표 복합 행 |
| Token API `live_ratio` + Integrated governance invoker + **CI tail** (브리핑 가드 다음 ~ job 끝) | **예** | — | §6 **포인터 행** + `.github/workflows/dual-regime-integrity.yml` SSOT |
| Track A Phase2 하네스 **pytest 스모크** (`test_track_a_harness_smoke_v1`) | **예** | `run_fact_lock_bundle` 기본 생략 가능 | 헬스 `-Include*` |
| Track A 미터링·상용 일일 산출 루프 (`run_track_a_commercialization_daily_chain.ps1` 등) | 아니오 | **번들 선택** / Windows `Register-TrackACommercializationDailyTask` | 헬스·스케줄 |
| AI BGM·상징/감정 M0·VA·fusion §3.8·렌즈 뮤직 분할 pytest(M1–M5·M32 시드·M20 오버레이·M26–M30 PoC 묶음 등) | **예** | `run_fact_lock_bundle` 기본에 전부 포함은 아님; CI `dual-regime-integrity` 오디오·VA·렌즈 뮤직 스텝과 정렬 | 헬스 `-Include*` |
| 렌즈 뮤직 M31 **strict** 프로세스 exit·일일 퓨전 말단 | 아니오 | **번들 선택**·`Invoke-TrackCMacroDailyFusion_v1.ps1` | `Run-LensMusicPromotionGateStagingStrict_v1.ps1` 등 |
| Aramaic MVP 일일·주간 **스케줄 실행 본체** | 아니오(Windows 스케줄) | 아니오 | **스케줄 + `Run-*WeeklyChain` 수동**; 레지스트리 `optional: true` |

**Aramaic MVP 운영 진입점(요약):** 일일 `scripts/Register-AramaicMvpDailyTask.ps1` · 임계 주간 `scripts/Register-AramaicMvpThresholdWeeklyTask.ps1` · 브리지 주간 `scripts/Register-AramaicMvpBridgeCoefWeeklyTask.ps1` — 상세 태스크명·시각은 `CONSTITUTION` Aramaic 표 해당 행. 레지스트리 행: `projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json`.

---

**상태**: 내부 작업 완료 잠금 (2026-03-30, ENTRY_16 Proxy Manual 승인 반영). 재개 트리거는 `ENTRY_07/08/16` 외부 판본 업데이트 이벤트로 제한한다.

---

## 문서 라벨 규칙 (Fact-Safe)

| 라벨 | 의미 | 사용 기준 |
|------|------|-----------|
| `[FACT]` | 재현·추적 가능한 진술 | 표의 경로·워크플로·pytest·CI·아티팩트로 검증된 항목; 잠금·완료 일자가 근거와 함께 기록됨 |
| `[HYPO]` | B-track 벤치·가설 | `CROSS_REF` rationale, 명리·사상 초안 필드, 미확정 표기(`—`, TBD); 승격·합선 전까지 단정 금지 |
| `[VISION]` | 경계·로드맵 | **여기서 끝 아님** 구간, Promotion Loop·상용 승격; 목표이지 현재 구현 단정 아님 |
| `[NON-MEDICAL]` | 비의료 고지 | 명리·사상·체질 문맥이 Phase 표에 포함되므로, 대외 인용 시 의료 효능·진단 주장과 분리 |

본 작업 리스트의 Phase 표는 위 라벨로 읽는다: `[x]` 체크와 테스트·경로가 붙은 행은 `[FACT]`에 가깝고, 격벽·승격 경계 문장은 `[VISION]`, 위성 코퍼스·테이블 미기입은 `[HYPO]`다.

---

## 연구·아이디어 인박스 (심사·토의 전용)

Phase 표·본 문서의 **잠금 완료 범위와 혼동 금지.** 아직 표에 올리지 않은 가설·정책·우선순위 토의는 `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md`에만 적고, 합의 후 이 워크리스트·`CONSTITUTION`·코드로 **승격**한다.
