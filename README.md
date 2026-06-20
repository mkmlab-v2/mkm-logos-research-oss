# MKM — Memory / Orchestration OS (Solo OSS)

**Hybrid context architecture for Cursor (and any IDE):** local shallow routing first, cloud deep fetch on demand — MIT, no counsel gate, no live-trading hooks.

License: **MIT License** — see [LICENSE](LICENSE)

> **Hook:** Stop dumping raw contexts into Cursor. Layer a lightweight routing pack on local Ollama (optional), use lane-scoped pins instead of full-paste, and treat the IDE as orchestration — not a token incinerator.

---

## Install ladder (pick your tier)

| Tier | You are… | What you get | Reproduce (exit 0 = OK) |
|------|----------|--------------|-------------------------|
| **0 · Smoke** | Fork curious | MIT, disclaimer, secret wall | `py scripts/check_mkm_solo_oss_release_readiness_v1.py` |
| **1 · Cursor-only** | Generic Cursor user | Stop pasting MISSION_LOG-sized blobs; lane inject (~4 pins) | `powershell -File scripts/Invoke-MkmCursorSessionUpgrade_v1.ps1` then bench below |
| **2 · Hybrid** | Ollama + IDE | Local classify / shallow path + Logos deep fetch (B-track) | `py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py` + optional chain in Tier 2 block |
| **3 · Contributor** | Extending the monorepo | Full scripts + tests per `B_subset` scope | `docs/final/artifacts/mkm_github_public_release_scope_v1_latest.json` |

### Tier 0 · Smoke (~5 min)

```powershell
cd C:\workspace
py scripts/check_mkm_solo_oss_release_readiness_v1.py
py scripts/check_mkm_secret_patterns_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_secret_scan_v1.ps1
```

### Tier 1 · Cursor-only (no Ollama required)

Resume / lane inject instead of naive full-paste:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmCursorSessionUpgrade_v1.ps1
# lane-specific: add -Lane oracle | ms | infra | design
```

Measure shallow savings vs naive baseline:

```powershell
py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py
# artifact: reports/mkm_ltm_orchestration_bench_v1_latest.json
```

Agent rules entry: `AGENTS.md` · resume pack: `docs/final/artifacts/mkm_chat_resume_pack_latest.md`

### Tier 2 · Hybrid (Ollama-friendly + deep fetch)

Bring your own models (e.g. `OLLAMA_MODEL` in `.env.example`). Shallow routing stays local; deep path may still call cloud IDE / API when you enable it.

```powershell
ollama create mkm-shallow-router-v1 -f docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt
py scripts/run_ollama_shallow_router_bench_v1.py --model mkm-shallow-router-v1 --fail-below-router-hit --min-router-hit-rate 0.75
py scripts/build_ollama_shallow_routing_oracle_gap_v1.py --max-oracle-gap 0.25
py scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py --include-deep-chain-dry-run
py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py
py scripts/run_question_semantic_rag_bridge_chain_v1.py --query "sample question" --query-id demo_q1 --skip-ann-lite
```

Optional showroom smoke (public chain):

```powershell
py scripts/run_showroom_job_topology_wiring_chain_v1.py --skip-pytest
py scripts/check_showroom_trust_viz_public_chain_v1.py
```

### Tier 3 · Contributor

Recommended first public slice: **`B_subset`** (bench + showroom + Logos smoke; counsel legacy excluded). Before any public push:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify-GitWorkspaceSanity.ps1
# public push only: scripts/Push-GitHub-Explicit.ps1 -Acknowledge
```

---

## Before vs After (Blind Cursor → Orchestrated Cursor)

| Topic | Blind Cursor (naive full-paste) | Orchestrated Cursor + MKM | Label |
|-------|----------------------------------|---------------------------|-------|
| **Mechanism** | Paste huge logs/docs every turn | Lane pins + router + capped insight JSON | **Measured** (bench scripts) |
| **Token cost** | ~52k-token naive baseline in repo fixture | Shallow inject **~99.6%** vs naive; orchestrated path **~33%** | **Measured** |
| **API spend** | Cloud billed for full context each turn | Local shallow reduces what reaches cloud; deep fetch is on demand | **Hybrid** — not “zero cost” (GPU/time still apply) |
| **Privacy** | Entire workspace text may leave the machine | Shallow path injects pins, not full MISSION_LOG; deep fetch still sends query/subgraph when enabled | **Hybrid** — not “coordinates only” for all paths |
| **Citation integrity** | Model may paraphrase sources | Logos B-track: `verse_id` + `quote_hash` guards (research lane) | **B-track** — not universal code hallucination block |

Footnotes: numbers from `py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py`. Do **not** cite DMF 5×–242×, counsel signoff, or Track A live readiness from these benches.

---

## Show HN / community blurb (copy-paste)

**Title:** MKM — stop full-pasting context into Cursor; measured ~99.6% shallow token savings

**One-liner:** Layer a routing pack on local Ollama (optional), inject lane pins instead of 50k-token pastes, deep-fetch only what you need — MIT, reproducible benches included.

**Body (short):**

```
Stop dumping raw contexts into Cursor IDE. MKM is a hybrid Memory/Orchestration OS:
- Shallow: lane-scoped ops pins (~4 nodes) instead of MISSION_LOG + CENTRAL paste
- Deep: subgraph router → RAG bridge → capped insight payload (on demand)
- Guard: research_only B-track walls — not live trading

Reproduce token savings in ~5 min:
  py scripts/check_mkm_solo_oss_release_readiness_v1.py
  py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py

MIT · SECURITY.md · measured metrics only (no DMF marketing multiples).
```

---

## Why this repo

Most agent stacks burn context on full paste. MKM treats memory like an OS:

| Layer | Role | What it does |
|-------|------|----------------|
| **Shallow** | Session inject | Lane-scoped ops pins (~4 nodes) instead of pasting MISSION_LOG + CENTRAL |
| **Deep** | Query path | Subgraph router → RAG bridge → capped insight payload |
| **Guard** | B-track walls | `research_only`, gold CPU eval, send-gate vocabulary — **not** auto live trading |

Architecture label: **local Ollama-friendly shallow routing + cloud IDE deep fetch** (hybrid; you bring your own models).

```mermaid
flowchart LR
  subgraph Shallow["Shallow — session inject"]
    Q[User / lane query] --> R[Ops memory router]
    R --> P[Lane pins ≤4 nodes]
  end
  subgraph Deep["Deep — query path"]
    Q2[Question] --> SR[Logos subgraph router]
    SR --> RB[RAG bridge bundle]
    RB --> IP[Insight payload caps]
  end
  subgraph Guard["Guard — B-track"]
    G[Gold CPU eval 12/12]
    C[Cap × gold regression]
    S[send_gate: OSS OPEN · live LOCKED]
  end
  P --> Agent[Agent context]
  IP --> Agent
  G --> Guard
  C --> Guard
```

---

## MKM-measured token bench (reproducible)

These numbers are **from this repo's scripts**, not external DMF/Mem0 marketing claims.

Reproduce:

```powershell
cd C:\workspace
py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py
```

Latest artifacts (regenerable):

| Metric | Result | Source |
|--------|--------|--------|
| Naive baseline (MISSION_LOG + CENTRAL paste) | ~52k tokens | `reports/mkm_ltm_orchestration_bench_v1_latest.json` |
| Shallow lane inject (mean) | **~99.6% savings** vs naive | same |
| Orchestrated query path (router+insight+bloom) | **~33% savings** vs naive | same |
| Insight cap ablation (ultra_min) | **~56% smaller** insight JSON vs baseline caps | `reports/mkm_ltm_insight_cap_ablation_bench_v1_latest.json` |
| Gold router eval | **12/12 pass** (CPU, B-track) | `reports/logos_gold_query_eval_v1_latest.json` |
| Cap × gold guard | **`baseline_production` only** (minimal regresses 5/12) | `reports/mkm_ltm_insight_cap_gold_regression_v1_latest.json` |

**Bench snapshot:** open the JSON paths above after running the bundle, or paste the table into your launch post — do not use external compression marketing multiples.

### Measured (this repo) vs external research (not shipped)

| Topic | **Measured here** | **External research only** |
|-------|-------------------|----------------------------|
| Token / context savings | Shallow ~99.6%, orchestrated ~33%, cap ablation ~56% — scripts above | DMF, Mem0, LLMLingua marketing multiples |
| Router quality | Gold CPU eval 12/12; cap guard = `baseline_production` only; shallow `routing_oracle_gap` **0.0** (8 fixtures), `cloud_skip_ratio` **1.0** | Shepherding / UCCI as product claims |
| Cost routing / offload | Shallow-only path documented; oracle gap shadow only | RouteLLM 2–3.6×, CE-CoLLM 84% offload (not MKM KPI) |
| Memory accuracy | Gold **12/12** (Logos domain); shallow router_hit **1.0** on golden v1.1 | ByteRover LoCoMo SOTA as product claim |
| Routing collapse (RCI) | not measured | EquiRouter RCI metric |
| Release gate | MIT + README + secret scan + `Verify-GitWorkspaceSanity.ps1` | Paid legal counsel signoff |
| Hybrid stack | Documented pattern: local shallow + IDE deep fetch | “Fully integrated Ollama+Cursor product” |
| Trading / grants | LOCKED / HOLD in send-gate vocabulary | Track A readiness from B-track bench |

Prior-art log template: `docs/research/nextgen_ltm_knowledge_os/PRIOR_ART_SEARCH_LOG_TEMPLATE.jsonl`

**Related work SSOT (B-track):** [`docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md`](docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md)

### Hybrid stack narrative (EN — whitepaper-safe)

> MKM is a **research-grade memory orchestration stack** for hybrid agent development: **shallow lane-scoped injection** replaces naive paste of full operator logs (~99.6% token reduction vs internal baseline, reproducible bench), while a **deep semantic fetch path** routes questions through capped insight bundles rather than raw corpus dumps. Local **Ollama** can emit a fixed JSON handoff (`ollama_shallow_router_output_v1`) before the IDE deep layer runs; measured shallow routing on eight golden fixtures shows **`routing_oracle_gap` 0.0** and **`cloud_skip_ratio` 1.0** in the latest shadow eval (B-track, not production SLA). The architecture rhymes with recent **tiered agent memory** (MemGPT, ByteRover) and **edge–cloud routing** literature (RouteLLM, CE-CoLLM), but MKM’s public claims are limited to **scripts with exit code 0** — not external compression multiples (LLMLingua, FrugalGPT) or unimplemented schedulers (NSGA-II). Track B guards (`research_only`, gold CPU eval, live trading LOCKED) remain in force.

---

## Full local smoke (all tiers)

```powershell
cd C:\workspace
py scripts/check_mkm_solo_oss_release_readiness_v1.py
py scripts/check_mkm_secret_patterns_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_secret_scan_v1.ps1
py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py
py -m pytest tests/test_ollama_shallow_routing_oracle_gap_v1.py tests/test_ollama_shallow_to_semantic_rag_e2e_v1.py -q
py scripts/run_showroom_job_topology_wiring_chain_v1.py --skip-pytest
py scripts/check_showroom_trust_viz_public_chain_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify-GitWorkspaceSanity.ps1
```

---

## Public release policy (solo operator)

- **OSS path:** MIT + this README + secret hygiene — **no paid legal counsel gate**
- **Deprecated:** `counsel_signoff` / lawyer email bundles as a release blocker
- **Still HOLD:** grants, customer contracts, **Track A live trading** (commander LOCKED)
- **GitHub push:** internal-first; public push only via `scripts/Push-GitHub-Explicit.ps1 -Acknowledge`
- **1st public scope (recommended):** `B_subset` in `docs/final/artifacts/mkm_github_public_release_scope_v1_latest.json` (counsel legacy excluded)

Policy artifact: `docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json`

---

## Security before you fork or publish

See [SECURITY.md](SECURITY.md). Never commit:

- `.env`, API keys, DPAPI secrets
- Local `MISSION_LOG.md`, machine-specific pointers
- Patient / grant / trading approval JSON

Root `.gitignore` blocks `.env` and local ops files. Before push:

```powershell
py scripts/check_mkm_secret_patterns_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_secret_scan_v1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify-GitWorkspaceSanity.ps1
pre-commit install   # optional — blocked if git core.hooksPath is set
pre-commit run gitleaks --all-files   # fallback when gitleaks not on PATH
```

---

## Phase A — Geometric Audit demo bundle

Research spikes (B-track, not production SLA):

```powershell
py scripts/spike_gematria_myeongri_blend_v0.py --stdout-only
py scripts/spike_sovereign_token_saving.py --stdout-only --samples 20 --seed 1
```

---

## Disclaimer

**EN:** This project is observational open-source software for research and developer testing. It is **not investment** advice and not medical advice. You are solely responsible for your use.

**KO:** 본 프로젝트는 연구 및 개발자 테스트 목적으로 제공되는 관측형 오픈소스 소프트웨어입니다. 어떠한 형태의 금융 투자 및 의료적 판단을 대신하지 않으며, 사용 중 발생하는 모든 책임은 사용자 본인에게 있습니다.

B-track outputs carry `[HYPO]` / `research_only` — not operational triggers.

---

## More docs

- Agent entry: `AGENTS.md`
- Send-gate vocabulary: `docs/final/artifacts/mkm_send_gate_vocabulary_v1_latest.json`
- Lens walls: 성경(Logos) / 명리 / 사상 — Final action = regime_map + ops gates
