# Compression 12M Learnings + Track B Playbook (Fact-Safe)

## 1) Session Fact Check (Completed Now)

- NotebookLM Hub B mirror sync executed:
  - Command path: `scripts/Invoke-HubBWeeklyMirror.ps1`
  - Latest log: `reports/hub_b_weekly_mirror_log.jsonl`
  - Latest record: `exit_code=0`, `step=vault_mirror` (2026-04-08 run)
- This document uses repository artifacts only; no unverifiable external performance claims.

## 2) What We Actually Built (12M compression lane snapshot)

Representative evidence (not exhaustive):

- General compression lane:
  - `docs/final/artifacts/general_compression_ab_result_summary_v1.json`
  - `docs/final/artifacts/general_compression_kpi_gate_v2.json`
  - `docs/final/artifacts/general_compression_benchmark_manifest_v1.json`
- Multi-lens compression lane:
  - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`
  - `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json`
- Genesis v3/v3.1 lane:
  - `docs/final/artifacts/comparison_summary_latest.json`
  - `docs/final/artifacts/genesis_v3_multimap_mixed_api_finance_v1_latest.json`
  - `docs/final/artifacts/tracka_vs_zstd_native_bench_latest.json`

## 3) Key Learnings (Hard Lessons)

1. **Claim boundary failure risk**
   - Repeated drift from simulation metrics to billing/VRAM marketing claims caused decision noise.
2. **Benchmark ordering mistake**
   - Build-first, market-check-later sequence created rework risk.
3. **Track A originality overestimation**
   - Shared dictionary patterns overlap with established techniques; moat is not in raw compression primitive.
4. **Control-plane value is real**
   - Route policy, isolation, fallback, audit artifacts are defensible operational value.
5. **Backend reality**
   - In current 10MB bench, native zstd dictionary path outperformed pointer pipeline (`tracka_vs_zstd_native_bench_latest.json`).

## 4) Anti-Repeat Guardrails (Mandatory)

Before any new compression feature merge, all 4 gates must pass:

1. **Market-overlap gate**
   - Must document overlap with native/vendor features and explain residual moat.
2. **Cost-of-operations gate**
   - Must quantify sync/update/deploy overhead vs measured benefit.
3. **Fact-safe claim gate**
   - Must map every external sentence to one artifact key/path.
4. **Fallback integrity gate**
   - Must show deterministic fallback behavior and `decode_check_ok` equivalent.

If any gate fails: feature remains research-only.

## 5) Track A Policy (Freeze / Narrow Use)

- Track A remains useful only as:
  - research scaffold,
  - control-plane policy harness,
  - niche constrained-network use cases.
- Track A is **not** default growth thesis for broad B2B billing reduction.
- Default backend preference in experiments: native zstd dictionary route when applicable.

## 6) Track B Execution Focus (What To Do Well Next)

Primary lane: quaternion restore/generalization research with strict governance.

Immediate evidence anchors:

- `docs/final/TRACKB_QUATERNION_RESTORE_DECISION_MEMO_V2_2026-04-08.md`
- `docs/final/artifacts/trackb_quaternion_two_stage_gate_v2.json`
- `docs/final/artifacts/trackb_quaternion_restore_bridge_v1.json`

Execution priorities:

1. Expand Track B stress grid (`length>=7`, higher OOV bins, adversarial variants).
2. Keep GO/HOLD research gate explicit; no production merge without separate latency/memory checks.
3. Produce weekly Track B delta bundle with:
   - exact restoration stats,
   - collision metrics,
   - runtime/memory trend,
   - failure cluster drift.

## 7) 14-Day Practical Plan

Day 1-2:
- Freeze Track A scope in decision docs (no new broad-market claims).
- Standardize one benchmark manifest template for Track B runs.

Day 3-7:
- Run expanded Track B grid and generate failure cluster diffs.
- Add reproducibility checks (seed, schema, command fingerprint).

Day 8-14:
- Prepare promotion-readiness memo for Track B (research-only status by default).
- Only if all gates pass, draft separate production readiness checklist.

## 8) Non-Negotiable Reporting Rule

All summaries must start with:

- what was measured,
- where the artifact is,
- what is explicitly out of scope.

No artifact, no claim.
