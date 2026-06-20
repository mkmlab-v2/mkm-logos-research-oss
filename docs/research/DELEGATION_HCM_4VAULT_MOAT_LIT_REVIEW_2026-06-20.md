# Delegation Deep Research — 4-Vault HCM · Verification Moat · Monetization [HYPO]

**Tier:** 1 (Cursor synthesis) · **Tier 0 input:** `docs/research/raw/delegation_hcm_4vault_moat_deep_sweep_2026-06-20.md`  
**Track:** B-track · `research_only` · `send_gate: HOLD`  
**Date:** 2026-06-20  
**Superseded for full catalog by:** `docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md` (62-paper merge)

---

## Executive gaps (3 bullets)

1. **Moat is governance + pointer federation**, not raw RAG — ByteRover (2604.01599) is closest commercial analog; MKM adds Vault 1 must_keep + Vault 2 `inject_policy: on_demand_only` with **no body merge into ops LTM**.
2. **`routing_oracle_gap 0.0` on 16 gold is in-domain only** — field literature (2602.03478, RouterBench 2403.12031) shows routing collapse OOD; Tier 2 delta = add OOD harness before any public "solved routing" claim.
3. **`citation_lock` ≠ cryptographic proof** — PCA / Vouch PAD-045 commit-then-generate proves **∈ committed corpus**, not semantic truth; feasible 1-person Layer 2–3 without exceeding MCP budget if plugins stay OFF.

---

## MKM measured vs field (Fact-Lock)

| Claim | MKM measured | Field benchmark | Public README safe? |
|-------|--------------|-----------------|-------------------|
| Token reduction | ~99.6% vs naive paste (orchestration bench) | Mem0 ~90% vs full context (2504.19413) | Yes, with scope |
| Routing quality | oracle_gap 0.0, 16/16 live shallow | RouteLLM up to 85% cost @ 95% quality (2406.18665) | Yes, domain-specific |
| 4-Vault uniqueness | Registry + catalog exit 0 | No paper defines identical 4-tier governance wall | Yes as **pattern**, not patent claim |
| Verification | arXiv citation_lock in md | PCA ~58% poison block post-commit | No crypto claim without code |

---

## Top 3 MKM deltas (Tier 2 candidates)

| Tag | Delta | Script target |
|-----|-------|---------------|
| `[Needs experiment]` | OOD routing gold (10 RouterBench-style prompts) | `tests/test_ollama_shallow_router_bench_v1.py` |
| `[Needs experiment]` | Merkle root manifest over Vault 2 resolved inject set | new spike under `scripts/` B-track only |
| `[Adoptable now]` | Overclaim firewall rows 11–14 in MERGED Part VIII | already in MERGED md |

---

## Monetization — 1-person realism (not marketing)

| Stage | Model | Field evidence | MKM fit |
|-------|-------|----------------|---------|
| 1 Open-core | MIT + enterprise envelope | GitGuardian CLI OSS → cloud seats | **Primary** — matches solo OSS policy |
| 2 Reference packs | Paid pointer catalogs | XPack MCP marketplace infra; demand unproven | **Optional** — Vault 2 packaging |
| 3 Desktop companion | Electron local runner | Continue → Cursor acqui; Windsurf subscription | **Low priority** — competes with Cursor host |

**High-ticket advisory** (enterprise governance install) is the realistic revenue line for 1-person — not mass consumer subscription or "token 99% savings" ads.

---

## Overclaim firewall (delegation-specific)

- Forbidden: "global 차세대 군림", "infra cost 0", "100% hallucination elimination", NSGA-II shipped, Merkle = citation_lock  
- Allowed: "aligns with MemGPT/ByteRover/HybridLLM literature"; "measured on repo-native bench exit 0"

---

## Reproducibility

```powershell
# Tier 0 raw (this delegation sweep)
# Read: docs/research/raw/delegation_hcm_4vault_moat_deep_sweep_2026-06-20.md

py scripts/run_mkm_merged_lit_review_gate_chain_v1.py --input docs/research/DELEGATION_HCM_4VAULT_MOAT_LIT_REVIEW_2026-06-20.md
py scripts/check_mkm_reference_pointer_registry_v1.py
powershell -File scripts\Run-OllamaShallowHybridReproduceBundle_v1.ps1 -IncludeDeepLive
```

---

*Track B · research_only · no Track A promotion · no SEND.*
