# MKM AI factsafe numbers (guardrail)

**Rule:** Every numeric claim in external-facing materials maps to a repo artifact path or is labeled **[DRAFT]** / **[HYPO]** and excluded from SLA language.

**Approved sources for KPI-style numbers:**

- Compression and multilens: `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`, `docs/final/artifacts/general_compression_kpi_gate_v2.json`, and paths listed under compression in `docs/final/P0_COMMERCIALIZATION_TRACKER.md`.
- Token API contract smoke outputs are regression evidence, not customer-facing latency SLA unless `bench_l1_api_load` (or VPS runbook) artifacts are cited with measurement context.

**Forbidden:** Quoting NotebookLM or chat summaries as numeric SSOT.
