# LG HS — Compression discipline deck outline (v1)

**Status:** `[DRAFT]` — slides only; not legal-approved external send.

**Generated:** 2026-05-18T20:52:57.482881Z

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

- RQ-016 bench floor **0.47** · bench_floor_ok **True** (≠ decision axis **0.49** · policy_ok **False**)
- 벤치 전역 절감 **47.5%** (40건, frozen KPI · Track A active)
- 평균 Jaccard **0.890**
- 승격 프로필 **`ssot_cap_0.45_top5_allowlist`** — ssot cap 0.45 on allowlist only (no global pin).
- Allowlist cases: cmp2_002, cmp2_004, cmp2_005, cmp2_006, cmp2_009.
- Jaccard = 단어 겹침 프록시; 의미 %·BOM 절감 단정 금지.

Evidence:
- `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`
- `docs/final/artifacts/compression_enterprise_executive_summary_v1.md`

## Slide 4: Shard Jaccard (frozen bench — not per-shard saving)

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

## Slide 5: Governance proofs (accurate)

- Lexicon **41,775** terms — deterministic must_keep join path.
- Shadow Auditor: **4** artifact contract pytest passes + frozen KPI scan (not **17/17**).
- Full 40-case re-bench: optional `--refresh-bench` (weekly chain), not every nightly default.
- RTT: VPS same-host p95 **~665–847 ms** (2026-05-16); loopback conc10 is smoke only — **no ms↔saving causality**.

Evidence:
- `reports/constitution/btrack_pilot/compression_shadow_auditor_latest.json`
- `docs/final/artifacts/compression_board_ms_correlation_report_v1_latest.json`

## Slide 6: Kill-Matrix (대외 금지)

- 환각 제거 · 리콜 0% · Zero-Liability
- 7,680 하드웨어 스윕(레포 SSOT 없으면)
- 하루 만에 자동차/로봇 이식 · 8.2ms(아티팩트 없으면)
- MMLU 점수만으로 양산 승인

## Slide 7: 클로징 — 다음 단계

- 로컬 벤치 기준선 → 타깃 보드 실측(RQ-017, [HYPO]) → 월간 Go/No-Go.
- 산출: 코드북·게이트 기준·실측 리포트·운영 가이드.
- 면책: Not investment advice; bench ≠ production SLA.

---

## Speaker note (one line)

> We sell artifact-bound discipline—not flashiest model scores.
