# MKM 압축 3층 신뢰 구조 — Track A 운영·v2 Trust Packet 초안·L1 연구 (LG HS 원페이저)

**INTERNAL ONLY · pre-legal-send** — LG HS 내부 검토용. 법무 송부 전 초안. 아티팩트·측정값만 근거; 계약·SLA·대외 약속 아님.

---

## 면책 (Disclaimers)

- **99%/100% 압축·47% 바닥 보장** 헤드라인 금지.
- **v2 Trust Packet** = OpenAPI 초안 + 실험 스텁 — **프로덕션 SLA·인증·요율·보존 없음**.
- **L1 ~57.87%** = `research_only` — 운영 복원 보장·Track A KPI 아님.
- **B-track** (`[HYPO]`)는 Track A active report **대체·B→Track A 자동 승격·실매매 합선 없음** (human review 별도).
- **은유**(장-뇌 등): 교육용 동형이상 — `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7 §3.

**발표 톤 (70/20/10):** 과제·측정 70% · 운영·거버넌스 20% · 비전 힌트 10%.

---

## 1) Track A — 승격 운영 베이스라인 (2026-05-18)

`promoted_operational_baseline` · MULTILENS ultra, bridge OFF, **Top5 ssot cap only**

**주장**
- Active SSOT: `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` — variant `ssot_cap_0.45_top5_allowlist`.
- V2 벤치 **~47.54%** global token saving, avg Jaccard **~0.890**, min Jaccard **~0.714** (동결 대비 min J 유지).
- RQ-016 **bench floor 0.47** 참조 **통과** (`bench_saving_floor_ok` in KPI summary); `ultra_saving_policy_ok`는 decision **0.49** 축 별도(혼용 금지).
- 국소 정책: `domain_relaxed_max_saving_overrides {ssot:0.45}` on case allowlist `cmp2_002,004,005,006,009` only — lexicon·bridge 변경 없음.

**주장하지 않음**
- 99%/100%·**고객/LG 47% 보장**; 전역 ssot 0.45(48.38% / min J 붕괴) 채택 주장; 벤치만 **프로덕션 SaaS SLA**.

**근거**
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`
- `docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json`
- `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`

---

## 2) v2 Trust Packet — 초안 (B-track)

`openapi_draft_plus_experimental_stub` · `[HYPO]`

**주장**
- Trust Packet = `compressed_text` + `residual_meta`; `loss_profile`로 절감 vs 동등 의도 분리.
- 스텁 `scripts/compression_token_api_v2_stub.py` — **v1 파일럿 기본**.

**주장하지 않음**
- 프로덕션 **SLA**, auth, rate limit, retention; v1 없이 v2 **단독 컷오버**.

**근거**
- `docs/final/openapi_token_compression_v2_draft.yaml`
- `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`

---

## 3) L1 연구 — 사이드채널 스파이크 (B-track)

`research_only_spike` · `[HYPO]`

**주장**
- L1 beam 스파이크 `avg_exact_restore_rate` **~57.87%** (research JSON).
- 사이드채널 wire = **연구 레인**, 상용 compress SLA 아님.

**주장하지 않음**
- Track A KPI·**고객 복원 보장**; 99%·**프로덕션급** 역디코딩.

**근거**
- `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`

---

## 4) B-track A-plan — 연구 이력 (승격 전후 구분)

`research_archive_plus_promotion_sweep` · `[HYPO]` for global pin only

**주장 (연구·아카이브)**
- 전역 ssot 0.45 pinpoint **~48.38%** — floor 0.47 통과 but **min J 회귀** → Track A **미채택**(아카이브).
- 승격 스윕 winner: **Top5 case allowlist** only → bench **~47.54%**, min J **~0.714** → **2026-05-18 human apply** to active.
- `run_ultra_compression_promotion_sweep_v1.py` / `apply_multilens_ultra_compression_track_a_promotion_v1.py` — signoff on disk.

**주장하지 않음**
- 전역 48.38%를 **현재 Track A**로 서술; 고객/LG **47% 보장**; Top5 내부 **미세 Jaccard 회귀**(4 cases) 무시.

**근거**
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json` (global pin archive)
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_PROMOTION_CANDIDATE_V1.json`
- `docs/final/artifacts/compression_b_track_bridge_evidence_summary_v1.json`

---

**정책:** `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` · `docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md`  
**아웃라인:** `docs/final/artifacts/lg_compression_trust_packet_onepager_outline_v1.json` (2026-05-19)  
**SOTA 4축 ↔ MKM (Inter-Agent Encoding):** `docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md` · 큐 **RQ-019** · **첫 기계어 문장:** `mkm_inter_agent_first_message_worked_example_v1.md`
