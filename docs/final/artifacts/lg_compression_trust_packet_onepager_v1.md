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

## 1) Track A — 운영 동결 베이스라인

`frozen_operational_baseline` · MULTILENS ultra, bridge OFF

**주장**
- 동결: `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`, bridge OFF.
- V2 벤치 **~46.84%** 토큰 절감, Jaccard **~0.899**; 바닥 **0.47** 참조, `ultra_saving_policy_ok=false` (측정 그대로).

**주장하지 않음**
- 99%/100%·바닥 **보장**; B-track **Track A 자동 승격**; 벤치만으로 **프로덕션 SaaS SLA**.

**근거**
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`
- `docs/final/artifacts/compression_b_track_bridge_evidence_summary_v1.json`

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

## 4) B-track A-plan — ssot 국소 cap 연구 (동결 Track A 미대체)

`research_pinpoint_not_track_a` · `[HYPO]`

**주장**
- `domain_relaxed_max_saving_overrides: {ssot: 0.45}` — **41k lexicon 미수정**, bridge OFF.
- V2 벤치 pinpoint **~48.38%** 절감 — **내부 floor 0.47 참조 통과**(pinpoint JSON만).
- `promotion_gates`: **human_review_required**, **auto_track_a_promotion_allowed=false**.

**주장하지 않음**
- Track A active **대체·자동 승격**; 고객/LG **47% 보장**; frozen **min Jaccard(0.714)** 유지.

**근거**
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_SSOT_RELAXED_CAP_PINPOINT_V1.json`
- `docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json`
- `docs/final/artifacts/compression_ssot_relaxed_cap_microgrid_v1_latest.json`

---

**정책:** `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` · `docs/final/artifacts/lg_hs_persuasion_module_v1_2026-05-08.md`  
**아웃라인:** `docs/final/artifacts/lg_compression_trust_packet_onepager_outline_v1.json` (2026-05-19)  
**SOTA 4축 ↔ MKM (Inter-Agent Encoding):** `docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md` · 큐 **RQ-019** · **첫 기계어 문장:** `mkm_inter_agent_first_message_worked_example_v1.md`
