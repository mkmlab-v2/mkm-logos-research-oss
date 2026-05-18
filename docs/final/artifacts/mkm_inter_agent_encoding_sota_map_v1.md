# MKM Inter-Agent Encoding — SOTA 문제 계열 ↔ 레포 컴포넌트 맵 (v1)

**INTERNAL ONLY · pre-legal-send** — IR·투자·LG **비전 10%** 슬롯용. 법무·PUBLIC_FACING 통과 전 대외 배포 금지.  
**상위:** `docs/final/artifacts/lg_compression_trust_packet_onepager_v1.md` · **큐:** `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-019**

---

## 면책

- **학술 논문·빅테크 제품과의 수치·순위 비교 없음** — 동일 **문제 계열** 정렬만.
- **99%/100% 무손실·토큰 0·프로덕션 SLA·「MKM Language 완성」** 대외 단정 금지 (`PUBLIC_FACING` v1.7 · CENTRAL 「41k·압축·LG — 통합 이해 한 장」).
- **Track A vs Track B** 합선 금지 — 절감률(Track A)과 Jaccard/복원(연구)을 한 문장에 섞지 말 것.

**발표 톤:** 70/20/10 — 측정·게이트 70% · 거버넌스 20% · Lingua Franca **힌트** 10%.

---

## 1) 글로벌 SOTA 문제 계열 (4축 · 비교 아님)

| # | 문제 계열 (학계·산업 공통) | 질문 한 줄 |
|---|---------------------------|------------|
| A | **시맨틱 통신·양자화 임베딩** | 텍스트 대신 **의미 좌표/벡터**를 보낼 수 있는가? |
| B | **신경·LLM 무손실(준무손실) 텍스트 압축** | 압축 후 **복원기**가 원문에 가깝게 되돌릴 수 있는가? |
| C | **멀티벡터·토큰 병합·슈퍼토큰** | 유사 의미를 **오프라인 병합**하고 런타임 ID를 짧게 쓸 수 있는가? |
| D | **프롬프트 압축 경제성** | API·지연 비용을 **측정 가능한 절감**으로 줄일 수 있는가? |

---

## 2) MKM 스택 ↔ 4축 매핑

| SOTA 축 | MKM 컴포넌트 (레포 이름) | 등급 | 오늘 말할 수 있는 것 | 말하면 안 되는 것 | 근거 (경로) |
|---------|-------------------------|------|---------------------|-----------------|----------------|
| **A** | S-L-K-M 4D 프레임 · (미래) opaque residual / semantic pointer | `[HYPO]` / `[VISION]` | 연구·도메인 **해석 프레임**; v2 `residual_meta`·`emit_semantic_pointer` **초안** | **4D만 주고받는 프로덕션 와이어** · QNN/사원수 **입증 완료** | `MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md` · `openapi_token_compression_v2_draft.yaml` · CENTRAL 4D policy OFF |
| **A′** | v2 **Trust Packet** (`compressed_text` + `residual_meta`) | `[FACT]` stub / `[VISION]` wire | OpenAPI 초안 + `compression_token_api_v2_stub.py` | **상용 SLA** · 에이전트 표준 MIME **완성** | `docs/final/openapi_token_compression_v2_draft.yaml` · `scripts/compression_token_api_v2_stub.py` |
| **B** | **L1 inverse decoder** + permutation-channel 스파이크 | `[FACT]` code / `[HYPO]` quality | 역복원 **실험·JSON** 존재; 메타 완전 시 **별도** 연구 스파이크 1.0 | **완벽 한국어 통역** · **무손실 LLM 압축 SOTA 달성** | `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json` (`research_only`, avg exact **~57.87%`) · `l1_permutation_channel_integrated_spike_latest.json` |
| **B′** | v1 `POST /v1/expand` echo | `[FACT]` | 페이로드 **원문 에코** (stub) | **텔레그램식 역복원** 의미 | `COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md` §10 |
| **C** | **41k-class master lexicon** + `atom_id` + bridge | `[FACT]` | Export·`evaluate_report` **must_keep** 보강 | **Strong 전체 목록** · **O(1)만으로 끝** | `scripts/export_master_codebook_v1.py` · `scripts/core/master_codebook_lexicon_v1_bridge.py` · `reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41775_rows_latest.json` |
| **C′** | 도메인 라우터 + `zone_*.json` 샤드 | `[FACT]` | **의미 훼손 통제** 압축 정책 | 단순 확률 드롭만 한다 | `scripts/core/domain_router.py` · `codebook/shards/` |
| **D** | Track A MULTILENS ultra 벤치 | `[FACT]` (동결) | **~47%** 토큰 절감 · Jaccard **~0.89** (bridge OFF, lexicon ON) | **상용 SaaS 완성** · **0.47=WATCH/HOLD** | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` · CENTRAL 「통합 이해 한 장」 |
| **D′** | L1 **msgpack side channel** wire | `[FACT]` research route | `POST /v1/research/l1_side_channel/wire` | Track A KPI · v2 SLA 일부 | `scripts/l1_side_channel_wire_codec.py` · `openapi_token_compression_stub_v1.yaml` |

**한 줄 아키텍처 (내부):** `41k lexicon + domain router` → **compress** → **Trust Packet (v2 draft)** → (연구) **L1 wire** → (연구) **inverse decoder** → 인간-facing copy.

---

## 3) MKM 차별 — 등급별 (대외용)

| 등급 | 내용 |
|------|------|
| **`[FACT]` 오늘** | 측정·재현 가능한 압축 벤치 · 렉시콘 Export/브리지 · v2/L1 **스키마·스텁·연구 엔드포인트** · 역복원 **게이트 JSON** · Fact-Lock·PUBLIC_FACING 면책 체계 |
| **`[VISION]` 12–24개월** | 에이전트 간 **단일 와이어 프로파일** · v2 **packet-only expand (Phase 2)** · 4D/임베딩을 **와이어 문법**으로 승격(AB·정책 입증 후) |
| **학계 대비 honest gap** | 신경 무손실 벤치 **동등 주장 없음** · 시맨틱 임베딩 **프로덕션 전송 없음** · Lingua Franca **미표준화** |

**차별 서사 (조건부):** 파편 SOTA 주제를 **한 레포·한 측정 체계·게이트 JSON** 안에 모으려는 것 — “논문 하나 이김”이 아니라 **상용화 경로를 측정 가능하게 쌓는 것**.

---

## 4) 백서·대외 Whitepaper 전 마일스톤 (기술)

| # | 마일스톤 | 완료 판정 (Fact-Lock) |
|---|----------|----------------------|
| M1 | **v2 Trust Packet Phase 2** — expand 입력 = packet only, 재조립 라운드트립 | **`[FACT]` 2026-05-19:** pytest **17 passed** · in-process roundtrip `expand_equals_stub_reconstructed=true` · `mkm_inter_agent_encoding_status_latest.json` → `rq_019_milestones_core_ready` |
| M2 | **Inter-agent wire profile v0** — `atom_id` 시퀀스 + 최소 `residual_meta` 스키마, `research_only` **아닌** 통합 리포트 1종 | **`[FACT]` 2026-05-19:** `docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json` · `docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json` |
| M3 | **Human decoder 게이트 공개** — exact rate·모드·한계 문장을 대외 허용 톤으로 고정 | 스파이크 JSON 갱신 + `PUBLIC_FACING` / Track C 부록 1문단 |

**RQ-019** `CLOSED` 조건: 위 M1–M3 + 법무·지휘관 승격 위치 합의.

**Worked example (첫 기계어 문장):** `mkm_inter_agent_first_message_worked_example_v1.md` + `.json` — `py scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py` (INTERNAL ONLY).

---

## 5) IR·제안서 한 줄 ([HYPO] · RQ-019)

- **KO:** 글로벌 연구가 다루는 LLM 간 **비용·지연** 문제에, MKM은 **원어 기반 고밀도 렉시콘**과 **도메인 통제 압축(측정된 벤치 JSON)** 위에 **Trust Packet 초안**을 올려 **에이전트 간 인코딩 레이어**로 확장 중입니다. 무손실 공통어·프로덕션 SLA는 **아직 주장하지 않습니다**.
- **EN:** For agent-to-agent cost and latency, MKM layers a **measured lexicon rail** and **governed compression baseline** under a **Trust Packet draft** toward an inter-agent encoding layer—not a claim of finished lingua franca or production SLA.

---

## 6) 금지 패턴 (Kill-Matrix 요약)

| 금지 문구 | 이유 |
|-----------|------|
| 토큰 소모 0 / 수백 배 빠른 AI 회의 | wire·LLM 비용 미측정·과장 |
| MKM Language / Lingua Franca **완성** | 프로토콜·표준 미고정 |
| Track A **상용 엔진 완성** | 스텁·SLA·v2 draft |
| 100% 무손실 복원·완벽 통역기 | L1 스파이크 **~58%** (`research_only`) |
| 4D = 시맨틱 임베딩 **이미 운영** | bridge policy OFF · HYPO 프레임 |
| 학계 SOTA **이김** / 빅테크 대비 우위 | 벤치 비교 SSOT 없음 |

---

**정책:** `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` · `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 「41k·압축·LG — 통합 이해 한 장」  
**schema:** `mkm_inter_agent_encoding_sota_map_v1` · **generated:** 2026-05-19
