# MKM Compression — Enterprise Executive Summary (v1)

**Status:** `[DRAFT]` — internal / B2B proposal use only until legal review against `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` (v1.7).  
**Not:** investment advice, medical claim, guaranteed latency, or “100% lossless” compression.  
**Evidence SSOT:** numbers below are copied from frozen artifacts at generation time; re-run bench commands before customer-facing use.

---

## One-line value proposition

MKM does not sell “a smarter model.” We sell a **governed compression layer**: measurable token economy, reconstruction fidelity gates, and frozen JSON artifacts your risk and platform teams can audit—without mixing bench KPIs into live trading triggers (FAIL-COMP-004).

---

## What we prove today (artifact-bound)

| Claim (conditional) | Metric | Source |
|---------------------|--------|--------|
| Track A token economy @ RQ-016 bench floor | **47.54%** global saving; `bench_saving_floor_ok: true` @ **0.47** | `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json` → `active_kpi` |
| Decision-axis saving gate (separate) | `ultra_saving_policy_ok: false` @ **0.49** — do not conflate with bench floor 0.47 | same KPI summary |
| Bench reconstruction proxy (Jaccard, not “meaning %”) | avg **~0.890**, min **~0.714** (40 cases) | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` |
| Sensitive-term integrity on bench | avg **1.0**, violations **0** | same active report |
| Track A promotion profile (2026-05-18) | `ssot_cap_0.45_top5_allowlist` — ssot relaxed cap on **5 low-saving cases only**; bridge OFF | `multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json` |
| Health case on bench (cmp2_014) | Jaccard **0.875** on active report | same active report, case `cmp2_014` |

**Do not say:** “88% meaning preserved,” “hallucination eliminated,” “world-unique OS,” or “NPU BOM savings proven” from this bench alone.

---

## Governance story (sales-safe framing)

1. **Narrow corridor:** We publish an explicit **bench** saving floor (**0.47**, `bench_saving_floor_ok`) distinct from the decision JSON **0.49** axis (`ultra_saving_policy_ok`)—not a post-hoc boast after the fact.  
2. **Fidelity guardrail:** Jaccard is a **word-overlap reconstruction proxy** on a fixed eval set; we pair it with sensitive-integrity checks and loss-pattern reports.  
3. **Selective precision:** Domains that need it (e.g. health copy) get **targeted codebook/shard tuning**—not a blunt “merge 54 shards” blast. Optional health-only bridge policy is **opt-in** (`--selective-bridge-policy-domains health`); default bench does not trade global saving for a single case.  
4. **Two-track honesty:** Track B literal / ultra-literal profiles exist for audit-heavy payloads; Track A `active_kpi` drives ops alarms only.

---

## Copy-paste paragraph (EN, proposal body)

> Our compression API is designed for enterprise operators who must cut LLM token spend without silent quality drift. On our current frozen benchmark (40 cases), Track A delivers approximately **47.5%** token reduction with `bench_saving_floor_ok` at published floor **0.47**, reconstruction fidelity avg Jaccard **~0.89** (min **~0.71**), and sensitive-term integrity **1.0** on that bench. Promotion uses a **case-allowlisted** ssot cap (five low-saving cases only), not a global domain blast. We ship decision JSON, KPI summaries, signoff records, and active reports so your team can reproduce results—not marketing slides alone. This is observability and governance for compression profiles; it is not a trading signal, clinical tool, or guarantee of lossless restoration in production.

---

## Copy-paste paragraph (KO, 내부 제안서 초안)

> MKM 압축 레이어는 “더 똑똑한 모델”이 아니라 **측정·게이트·동결 아티팩트**를 제공합니다. 현행 Track A SSOT(40건 벤치)는 전역 토큰 절감 **약 47.5%**, RQ-016 벤치 하한 **0.47** 충족(`bench_saving_floor_ok`), avg/min Jaccard **약 0.89 / 0.71**, 민감어 무결성 **1.0**입니다. `ultra_saving_policy_ok`(0.49 축)와 **혼용하지 않습니다**. 승격 프로필은 ssot cap **0.45**를 저절감 Top5 케이스에만 적용합니다. 복원 품질은 Jaccard(단어 겹침 프록시)로 보고하며 “의미 N%”로 단정하지 않습니다. 본선 트레이딩·실매매와 벤치 KPI는 합선하지 않습니다.

---

## Disclaimers (required on every external slide)

- Not investment advice; not medical diagnosis/treatment.  
- Bench metrics ≠ production SLA until separately measured on your payloads and hardware.  
- `go_no_go` in decision JSON is **not** auto-derived from KPI alone (Fact-Lock §6.1).  
- Jaccard measures lexical overlap on eval text—not semantic equivalence or model-level determinism of generative LLM calls.

---

## Roadmap (`[HYPO]` / B-track — not shipped)

| Initiative | Intent |
|------------|--------|
| **Meta-policy** | Auto-align lexicon/shard per incoming domain without per-domain manual tuning |
| **Board latency correlation** | Link token savings to **measured ms** on target NPU/edge hardware (not loopback API RTT alone) |
| **Shadow Auditor** | **Implemented (RQ-018):** `scripts/run_compression_shadow_auditor_v1.py` → `compression_research_metaphor_debug_queue.jsonl` (B-track; no auto-promote) |

See `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` **RQ-016–RQ-018**. Nightly: `Register-CompressionShadowAuditorDailyTask.ps1`.

---

## Reproduce (engineering)

```text
py scripts/run_ultra_compression_default.py
py scripts/report_ultra_compression_kpi_summary.py
```

Signoff auto-load: `multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json` (universal mode).

Policy / tracks: `docs/final/COMPRESSION_SLA_POLICY_V1.md`  
Track C business frame: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.1.1–§3.1.3 (governance · global positioning · execution schedule)

**Generated:** 2026-05-16 · schema `compression_enterprise_executive_summary_v1`
