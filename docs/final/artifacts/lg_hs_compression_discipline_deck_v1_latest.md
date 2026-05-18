# LG HS — Compression discipline deck outline (v1.1 · 9 slides)

**Status:** `[DRAFT]` — slides only; not legal-approved external send.

**Generated:** 2026-05-18T21:07:47.322596Z

**Tone:** 70/20/10 · manufacturing language · `lg_hs_persuasion_module_v1_2026-05-08.md`

---

## Slide 1: 오프닝 — 제조업 언어

- 우리는 가장 화려한 모델 점수가 아니라, 운영 가능한 AI 디시플린을 제안합니다.
- 벤치·정책 하한·감사 로그는 동결 아티팩트로 재현합니다.
- [DRAFT] 법무·PUBLIC_FACING v1.7 통과 전 대외 배포 금지.

## Slide 2: 문제 정의 (70%)

- 가전·플랫폼 AI의 리스크: 오작동 전이, 지연 스파이크, 양산 정합성.
- 벤치만 좋은 모델은 양산 현장에서 방어 불가.
- WATCH/HOLD·재질문 정책 = 실행 전 리스크 차단(투자조언 아님).

## Slide 3: 압축 거버넌스 증거 (조건부 수치)

- Policy floor **0.47** · `ultra_saving_policy_ok` **True** (aligned with RQ-016 bench when promoted).
- 벤치 전역 절감 **47.5%** (40건, frozen KPI · Track A active)
- 평균 Jaccard **0.890**
- 승격 프로필 **`ssot_cap_0.45_top5_allowlist`** — ssot cap 0.45 on allowlist only (no global pin).
- Allowlist cases: cmp2_002, cmp2_004, cmp2_005, cmp2_006, cmp2_009.
- Jaccard = 단어 겹침 프록시; 의미 %·BOM 절감 단정 금지.

Evidence:
- `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`
- `docs/final/artifacts/compression_enterprise_executive_summary_v1.md`

## Slide 4: Moat — LLM 확률 압축 vs MKM 결정론 (Track A)

- **질문 방어:** “단어장 만들면 끝 아니냐?” → 연료(41k) + 라우팅(JSON) + 동결 벤치 + 제어층(22장) 조립.
- | 축 | LLM 확률 압축 | MKM 결정론 (Track A 동결) |
- | 엔진 | LLM/벡터로 중요 토큰 **확률 선택** | **41,775** lookup + **키워드→샤드 1개** + 고정 압축 엔진 |
- | 재현·비용 | 모델/API에 따라 변동 | 동일 `run_config` → JSON 리포트 재현; **LLM 추론 없음** |
- | 동결 KPI | 벤더별 상이 | 40건 벤치 · 절감 **47.5%** · Jaccard **0.890** · `apply_gematria_4d_bridge_policy: false` |
- | 제어 | 요약·절감 중심인 경우 많음 | **WATCH/HOLD** = 22장 실행 게이트 (**≠** 7장 floor **0.47**) |
- 각주: 0.47 = 절감 하한; WATCH/HOLD = 실행 전 차단(가전·22장).

Evidence:
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`
- `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`

## Slide 5: Plug-in scalability — 41k + zone JSON 팩

- **Plug-in scalability:** OS 커널처럼 **41k 글로벌 연료 고정** + 산업별 **`zone_*.json` 샤드 팩** 플러그인.
- 41k(Logos 원어 Export)에 없는 B2B 용어 → 샤드 `must_keep_hard_terms` (예: `zone_f_code`, `zone_a_scm`, **`zone_g_health`**) — **not** `zone_c_health`.
- 런타임: **41k lookup 항상 ON** + 라우터가 `routing_keywords` 점수로 **최적 샤드 1개** 선택 (`scripts/core/domain_router.py`) — 통짜 사전 스왑 ❌.
- 혼합 도메인 문서: **41k 공통층 + 1차 샤드**; multi-shard union = **로드맵**(Track A 동결은 single-route).
- vs LoRA/거대 교체 사전: **KB급 JSON 팩** — **런타임 파인튜닝·가중치 스왑 없음** (Export·큐레이션 비용은 별도).

Evidence:
- `codebook/shards/zone_*.json`
- `scripts/core/domain_router.py`
- `scripts/core/master_codebook_lexicon_v1_bridge.py`

## Slide 6: Shard Jaccard (frozen bench — not per-shard saving)

- 40-case frozen bench — **token saving is global only** (47.5%); shard rows are Jaccard only.
- Jaccard = overlap proxy; not semantic meaning %.
- `zone_a_scm` (n=12): avg **0.866**, min **0.667**
- `zone_b_timing` (n=2): avg **0.845**, min **0.786**
- `zone_c_hangul` (n=14): avg **0.903**, min **0.750**
- `zone_d_ssot` (n=8): avg **0.875**, min **0.714**
- `zone_g_health` (n=4): avg **0.922**, min **0.875**
- Global min Jaccard **0.667** (worst case on bench).

Evidence:
- `docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json`
- `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`

## Slide 7: Governance proofs (accurate)

- Lexicon **41,775** terms — deterministic must_keep join path.
- Shadow Auditor: **4** artifact contract pytest passes + frozen KPI scan (not **17/17**).
- Full 40-case re-bench: optional `--refresh-bench` (weekly chain), not every nightly default.
- RTT: VPS same-host p95 **~665–847 ms** (2026-05-16); loopback conc10 is smoke only — **no ms↔saving causality**.

Evidence:
- `reports/constitution/btrack_pilot/compression_shadow_auditor_latest.json`
- `docs/final/artifacts/compression_board_ms_correlation_report_v1_latest.json`

## Slide 8: Kill-Matrix (대외 금지)

- 환각 제거 · 리콜 0% · Zero-Liability
- 7,680 하드웨어 스윕(레포 SSOT 없으면)
- 하루 만에 자동차/로봇 이식 · 8.2ms(아티팩트 없으면)
- MMLU 점수만으로 양산 승인
- 학습 비용 0원 · 멀티 샤드 동시 활성화 · zone_c_health · Jaccard 0.899

## Slide 9: 클로징 — 다음 단계

- 로컬 벤치 기준선 → 타깃 보드 실측(RQ-017, [HYPO]) → 월간 Go/No-Go.
- 산출: 코드북·게이트 기준·실측 리포트·운영 가이드.
- 면책: Not investment advice; bench ≠ production SLA.

---

## Speaker note (one line)

> We sell artifact-bound discipline—not flashiest model scores.

Moat slides 4–5 full scripts: `lg_hs_ir_moat_speaker_pack_v1_latest.md`.
