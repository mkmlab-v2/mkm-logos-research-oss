# Compression Two-Track SLA Policy (v1)

**Status:** operational policy (v1)  
**Aligned with:** `docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md`, `docs/final/artifacts/compression_alarm_thresholds_v1.json`  
**Not:** a guarantee of trading edge, legal advice, or literal replication of all payloads without separate audits.

## 1. Purpose

Separate **service expectations** for (A) default multi-lens bench / ops compression and (B) **domain-literal** payloads where token economy is secondary to reconstructive fidelity and auditability.

## 2. Track definitions

### Track A — Universal ops (default)

- **Role:** Primary benchmark profile driven by `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json` and refreshed by `scripts/run_ultra_compression_default.py` with `--mode universal` (default).
- **Quality targets (indicative, from archived KPI snapshots):** sensitive integrity 1.0; reconstruction fidelity (Jaccard) on the order of ~0.73; global token saving rate near ~0.49 with policy floor 0.49 per Fact-Lock §6.1.
- **Artifacts:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`, `reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`.

### Track B — Literal-priority (conservative)

- **Role:** Conservative compression: lower saving caps, strategy `C`, intensity `high`, to prioritize fidelity over savings. Invoked by `scripts/run_ultra_compression_default.py --mode literal`.
- **Targets (engineering bounds, not certifying legal/medical correctness):** maximize Jaccard toward 1.0; accept saving rates roughly in the 0.10–0.30 band when the experimental compressor honors caps; integrity remains gated by the same `must_keep` / sensitive logic as Track A.
- **Artifacts:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json` (does not overwrite Track A active report).
- **Example bench snapshot (V2 input, refresh to reproduce):** on a representative run, average reconstruction fidelity (Jaccard) moved to approximately **0.92** with global token saving near **0.25** — illustrative only; re-run the script for current numbers.

### Track B — Ultra-Literal (research, precision-first)

- **Role:** Same strategy `C` / intensity `high`, but **much lower saving caps** (order ~0.06 general/sensitive, ~0.08 Hangul on the reference implementation) so reconstruction Jaccard approaches **1.0** on the V2 bench, at the cost of token economy. Targets **precision-heavy proxy bands** on that bench: `cmp2_001`–`010` (EN policy/ops, finance-adjacent) and `cmp2_011`–`040` (Korean medical/sasang lines). Subset aggregates are written under `compression_metrics.precision_domain_subsets` in the active report.
- **Command:** `py scripts/run_ultra_compression_default.py --mode ultra-literal`
- **Artifact:** `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json` (does not overwrite Track A or Track B literal reports).
- **Automation (optional):** `scripts/run_compression_automation_chain.ps1 -IncludeUltraLiteralTrack` (also runs loss-pattern report for `--sla-track ultra_literal`).
- **Boundaries:** Research profile only — not a compliance seal for regulated medical or financial advice; webhook alarms remain **Track A `active_kpi`** per section 3.

## 3. Boundaries

- Track B does **not** replace dedicated legal, wallet, or clinical verification pipelines. It is a **compression profile**, not a compliance seal.
- `go_no_go` in decision JSON is **not** auto-derived from KPI alone (Fact-Lock §6.1).
- Legacy `ultra_saving_50_ok` vs policy-min 0.49: Track A may satisfy policy while failing the legacy 50% flag; document thresholds in `compression_alarm_thresholds_v1.json`.

## 4. Operational commands

| Track | Command |
|-------|---------|
| A | `py scripts/run_ultra_compression_default.py` or `--mode universal` |
| B | `py scripts/run_ultra_compression_default.py --mode literal` |
| B ultra-literal (research) | `py scripts/run_ultra_compression_default.py --mode ultra-literal` |
| Full chain + Track B + dual loss reports | `scripts/run_compression_automation_chain.ps1 -IncludeLiteralTrack` |
| Full chain + ultra-literal + loss patterns | `scripts/run_compression_automation_chain.ps1 -IncludeUltraLiteralTrack` (can combine with `-IncludeLiteralTrack`) |
| Workspace health + two-track compression | `scripts/run_workspace_automation_health.ps1 -IncludeCompressionKpi -IncludeLiteralTrack` (optional; adds runtime vs `-IncludeCompressionKpi` alone) |

KPI summary (`reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json`) includes optional `literal_kpi` when `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json` is present.

Webhook alarm (`send_compression_kpi_alarm_if_needed.ps1`) evaluates **Track A `active_kpi` only**; Track B low saving does not by itself trigger that alarm.

## 5. Loss-pattern diagnostics

- **Script:** `scripts/report_compression_jaccard_loss_patterns.py`  
- **Output (Track A):** `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_latest.json` (`--sla-track universal`)  
- **Output (Track B):** `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_literal_latest.json` (`--sla-track literal`)  
- **Input join:** bench input `MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json` + active report for reconstructed text.

## 6. Revision

Bump version when caps, artifact paths, or Track B semantics change; cross-link from this file to Fact-Lock changelog entries.
