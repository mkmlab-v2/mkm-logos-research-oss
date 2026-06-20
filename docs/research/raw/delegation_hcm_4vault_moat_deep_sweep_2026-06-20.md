# Edge-Cloud Hierarchical Context Management (HCM) · 4-Vault Pointer Federation · Verification Moats

**File target:** `docs/research/raw/delegation_hcm_4vault_moat_deep_sweep_2026-06-20.md`  
**Track:** B-track · `research_only` · `send_gate: HOLD`  
**Sweep date:** 2026-06-20 · **Sources:** 32 (arXiv/ACL/IEEE/OSS)  
**Method:** Tier 0 web sweep (2024–2026) + MKM measured-fact crosswalk from `NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md`

---

## Research Value Assessment

**Research value: high** — Convergent prior art across MemGPT/Letta, ByteRover, AgentFold/HiAgent, HybridLLM/RouteLLM, KV-cache tiers, and Merkle/provenance RAG; closest gap to MKM is **governed pointer federation + shallow inject policy**, not raw vector RAG.

---

## Executive Matrix

| Dimension | Field consensus (2024–26) | Closest academic/commercial analog | MKM 4-Vault posture | Gap / risk |
|-----------|---------------------------|-----------------------------------|---------------------|------------|
| **HCM metaphor** | Context = RAM; external stores = disk; agent pages in/out (MemGPT) | MemGPT (2310.08560), Letta blocks, CoALA (2309.02427) | Vault 1 governance LTM + Vault 3 shallow τ | MKM adds **policy-gated inject** not in MemGPT |
| **Shallow routing** | Index/pointer routing before full fetch (H-MEM, ByteRover tiers) | H-MEM (2507.22925), ByteRover (2604.01599) | Ollama 8B emits routing JSON; Vault 2 pointers `on_demand_only` | Oracle 0.0 is **16-case domain gold**, not RouterBench |
| **Deep fetch** | On-demand expansion of folded/summarized state | HiAgent (2408.09559), AgentFold (2510.24699), Context-Folding (2510.11967) | Vault 4 query RAG + Vault 2 cold pointer resolve | No published **4-tier governance wall** |
| **Context folding** | Proactive multi-scale condensation beats append-only | AgentFold, FoldGRPO, HiAgent, Confucius (2512.10398) | Shallow inject 99.6% token reduction vs naive paste (bench) | Folding loss irreversible without pointer backrefs |
| **Edge-cloud offload** | SLM routes/partitions; cloud for hard tokens | HybridLLM (2404.14618), CE-CoLLM (2411.02829), survey (2507.16731) | Local 8B coordinator + cloud deep | Routing collapse at scale (2602.03478) |
| **KV migration** | Multi-tier GPU→CPU→SSD; prefix reuse | LMCache (2510.09665), KVSwap, MTDS | Not MKM core; infra lane | Latency dominates naive split-model |
| **Verification moat** | Merkle/signatures prove **provenance**, not truth | PCA, Vouch PAD-045, RAG-Shield, neleus-db | `citation_lock` ≠ crypto proof | Need commit-before-generate + inclusion proofs |
| **Memory decay** | Ebbinghaus + reinforcement + utility gating | Oblivion (2604.00131), 2404.00573, MemoryBank lineage | LTM graph + ops pins (must_keep) | ω-decay formulas not shipped as MKM gate |
| **Monetization** | OSS distribution → cloud/enterprise seats | GitGuardian, Sourcegraph, Continue, ByteRover | MIT solo OSS policy | Desktop companion ≠ automatic revenue |

---

## MKM Measured Facts (compare to literature)

| MKM metric | Value | Literature comparator | Interpretation |
|------------|-------|----------------------|----------------|
| Shallow inject vs naive paste | **~99.6%** token reduction | Mem0: **~90%** token cost vs full-context (2504.19413); AgentFold: **~7k tokens after 100 turns** | MKM bench is **orchestration inject**, not LoCoMo QA |
| Orchestrated path vs naive | **~33%** of naive tokens | Context-Folding: **10×** smaller active context at parity | Same efficiency class, different task |
| `routing_oracle_gap` | **0.0** on **16 golden** | RouterBench oracle: near-optimal cost (2403.12031); EquiRouter fixes collapse (2602.03478) | MKM gap is **in-domain**; field shows large oracle–router gap OOD |
| 4-Vault registry | `inject_policy: on_demand_only` on Vault 2 | ByteRover: tiered cache→BM25→LLM; H-MEM: index routing | MKM novelty = **governance + cold pointer contract** |
| Gold router | 12/12 CPU (logos gold eval) | RouteLLM: up to **85%** cost cut at **95%** GPT-4 quality (2406.18665) | MKM gold is **narrow**; RouteLLM is broad benchmarks |

---

## Prior Art Gap Mapping Table

| Paper / System | arXiv / URL | Method | MKM Vault mapping | Gap vs MKM |
|----------------|-------------|--------|-------------------|------------|
| **MemGPT** | [2310.08560](https://arxiv.org/abs/2310.08560) | OS-style main vs archival/recall; FIFO queue; function paging | V1↔V4 boundary; V3 working set | No governance pins; no cold **pointer-only** vault |
| **Letta / MemGPT blocks** | [letta.com/blog/memory-blocks](https://www.letta.com/blog/memory-blocks) | Persisted editable blocks; compiled context | V1 ops pins + V3 resume | No `inject_policy`; no B-track lens walls |
| **CoALA** | [2309.02427](https://arxiv.org/abs/2309.02427) | Working/episodic/semantic/procedural taxonomy | 4-Vault **conceptual** map | Taxonomy only—no pointer federation |
| **Mem0** | [2504.19413](https://arxiv.org/abs/2504.19413) | Extract/consolidate/retrieve; graph variant | V4 query memory | Cloud-centric; no governance LTM separation |
| **Zep / Graphiti** | [2501.13956](https://arxiv.org/abs/2501.13956) | Bi-temporal KG; hybrid retrieval | V4 + provenance edges | Enterprise service; not IDE shallow-inject |
| **H-MEM** | [2507.22925](https://arxiv.org/abs/2507.22925) | 4-layer index routing (domain→episode) | V2 pointer index + V4 deep | Vectors required; no cold external doc pointers |
| **ByteRover** | [2604.01599](https://arxiv.org/html/2604.01599v1) | LLM-curated Context Tree; 5-tier retrieval | **Closest:** V2 tree + V3 shallow + V4 deep | No ops governance vault; no lens 격벽 |
| **HiAgent** | [2408.09559](https://arxiv.org/abs/2408.09559) | Subgoal chunks; summarize + trajectory retrieval | V3 working memory folding | In-trial only; no cross-session governance LTM |
| **AgentFold** | [2510.24699](https://arxiv.org/abs/2510.24699) | Granular condensation + deep consolidation | V3 compaction policy | Web-agent trained; no pointer provenance |
| **Context-Folding / FoldGRPO** | [2510.11967](https://arxiv.org/abs/2510.11967) | branch/return; RL process rewards | V3 branch isolation | Requires RL training; MKM uses rules+gold |
| **GCC (Git Context Controller)** | [2508.00031](https://arxiv.org/html/2508.00031v2) | `.GCC/` filesystem; COMMIT/BRANCH/CONTEXT | V1+V3 file-backed memory | No 4-vault inject policy or RAG lane |
| **Confucius Code Agent** | [2512.10398](https://arxiv.org/html/2512.10398v1) | Hierarchical scopes + Architect compression | V3 budget + planner compaction | Industrial repo scale; no B-track guards |
| **HybridLLM** | [2404.14618](https://arxiv.org/abs/2404.14618) | Query difficulty router; quality/cost dial | Local 8B → cloud escalation | **40%** fewer large-model calls; 10% quality drop at large gap |
| **RouteLLM** | [2406.18665](https://arxiv.org/abs/2406.18665) | Preference-trained 2-model router | Shallow router analog | Learned router; MKM uses gold+rules |
| **RouterBench** | [2403.12031](https://arxiv.org/abs/2403.12031) | 405k outcomes; cost-performance oracle | Eval harness target | Oracle ≠ deployed router; collapse documented |
| **CE-CoLLM** | [2411.02829](https://arxiv.org/html/2411.02829) | Early-exit + cloud context mgmt | Edge-cloud handoff pattern | **13.8%** latency cut; comms bottleneck |
| **Edge SLM survey** | [2507.16731](https://arxiv.org/html/2507.16731) | Routing/offload/speculative taxonomy | MKM architecture placement | Survey—not implementable contract |
| **LMCache** | [2510.09665](https://arxiv.org/pdf/2510.09665) | KV off GPU; prefix reuse | Infra (not vault) | **15×** throughput w/ vLLM |
| **Oblivion** | [2604.00131](https://arxiv.org/html/2604.00131v2) | Decay-driven cluster retention | V1 consolidation candidate | Soft eviction—not MKM must_keep pins |
| **Human-like consolidation** | [2404.00573](https://arxiv.org/html/2404.00573v1) | Dynamic recall probability model | V1 temporal relevance | Dialogue-centric; not IDE ops |
| **From Spark to Fire** | [2603.04474](https://arxiv.org/html/2603.04474) | Error cascade graph; genealogy governance | Multi-agent handoff risk | **32%→89%** defense with plugin |
| **Routing collapse** | [2602.03478](https://arxiv.org/html/2602.03478) | Routers degenerate to strongest model | **Critical for 8B coordinator** | Oracle uses GPT-4 **<20%** on RouterBench |
| **PCA (Proof-Carrying Answers)** | [github.com/HimJoe/proof-carrying-answers](https://github.com/HimJoe/proof-carrying-answers) | Ed25519 + Merkle + FAISS | Verification moat beyond `citation_lock` | Proves **∈ corpus**, not semantic truth (**58%** poison block) |
| **Vouch PAD-045** | [vouch-protocol PAD-045](https://github.com/vouch-protocol/vouch/blob/main/docs/disclosures/PAD-045-proof-of-non-hallucination-retrieval-anchoring.md) | Commit retrieval root before generation | Local→cloud handoff attestation | Accountability, not hallucination prevention |
| **neleus-db** | [github.com/auralshin/neleus-db](https://github.com/auralshin/neleus-db) | BLAKE3 content-addressed; Merkle state | 1-person-feasible provenance store | Research OSS; not IDE-integrated |
| **RAG-Shield** | [github.com/SidereusHu/RAG-Shield](https://github.com/SidereusHu/RAG-Shield) | Merkle + vector commitment + forensics | Defense-in-depth reference | Heavy; overkill for solo dev |
| **Governance Envelopes** | [sanna.dev/papers/governance-envelopes](https://sanna.dev/papers/governance-envelopes.html) | Signed receipt bundles for handoff | Agent-to-agent verify before admit | Complements Merkle, not replacement |

---

## Mathematical Formulas: Memory Consolidation & Decay

### 1. Ebbinghaus forgetting (baseline)

\[
R(t) = e^{-t/s}
\]

- \(R\): retention; \(t\): elapsed time; \(s\): memory stability  
- Source: Ebbinghaus (1885); agent implementations: MemoryBank lineage (2305.10250)

### 2. Exponential strength decay (implementation standard)

\[
S(t) = S_0 \cdot e^{-\lambda t}, \quad \lambda = \frac{\ln 2}{t_{1/2}}
\]

### 3. Dynamic human-like consolidation (MKM-relevant ω-decay family)

From [2404.00573](https://arxiv.org/html/2404.00573v1):

\[
p_n(t) = \frac{1 - \exp(-r \cdot e^{-t/g_n})}{1 - e^{-1}}
\]

\[
g_n = g_{n-1} + \frac{1 - e^{-t}}{1 + e^{-t}}, \quad g_0 = 1
\]

### 4. Oblivion cluster retention (2604.00131)

\[
R_t(c) = f\!\left(U_t(c), F_t(c), n_t(c), T\right)
\]

### 5. Hybrid routing cost-quality (edge coordinator)

\[
\min_{\pi} \; \mathbb{E}[c(\pi(q))] \quad \text{s.t.} \quad \mathbb{E}[\text{quality}(\pi(q))] \geq \tau
\]

---

## Top 3 Vulnerability Remediations (1-person repo, feasible)

1. **Cascade-not-route for cloud escalation** — HybridLLM (2404.14618); extend shallow reproduce bundle with OOD cases  
2. **Minimal provenance moat: commit-then-generate** — PCA / Vouch PAD-045; Ed25519 + Merkle over Vault 2 resolved set; **not** hallucination elimination  
3. **Golden + budget regression harness** — RouterBench-style OOD + budget sweep; report `routing_oracle_gap` separately from Track A raw gate  

---

## Monetization Reality Check (measured vs hype)

| Vendor | Open surface | Measured monetization | Hype trap |
|--------|--------------|----------------------|-----------|
| **GitGuardian** | `ggshield` MIT CLI | Cloud **~$60/dev/mo**; enterprise contracts | "Free OSS" = CLI only |
| **Sourcegraph** | Cody Apache 2.0 | Enterprise-only; Free/Pro sunset 2025 | Open Cody did not sustain indie tiers |
| **Continue.dev** | Apache 2.0 IDE ext | Acquired by Cursor 2026; Hub Team **$20/seat** | OSS → acqui path |
| **ByteRover** | CLI OSS + cloud sync | Hosted memory commercial | Vendor-reported benchmarks |

**MKM implication (B-track, 1-person):** MIT core + optional reference pointer packs + **enterprise governance consulting** — not "infra cost zero" or consumer desktop subscription vs Cursor.

---

## MKM Overclaims to Avoid

| Claim | Safer wording |
|-------|---------------|
| "99% cloud cost zero" | Shallow inject ~99.6% vs naive paste **in orchestration bench** |
| "100% hallucination elimination" | Merkle proves ∈ corpus; semantic verify separate |
| `citation_lock` = crypto proof | Policy lock; crypto attestation is optional Layer 2–3 |
| `routing_oracle_gap 0.0` = solved routing | 0.0 on **16 golden** shallow-router regression only |

---

## Sources (32)

1. MemGPT — https://arxiv.org/abs/2310.08560  
2. CoALA — https://arxiv.org/abs/2309.02427  
3. Mem0 — https://arxiv.org/abs/2504.19413  
4. Zep — https://arxiv.org/abs/2501.13956  
5. H-MEM — https://arxiv.org/abs/2507.22925  
6. ByteRover — https://arxiv.org/html/2604.01599v1  
7. HiAgent — https://arxiv.org/abs/2408.09559  
8. AgentFold — https://arxiv.org/abs/2510.24699  
9. Context-Folding — https://arxiv.org/abs/2510.11967  
10. GCC — https://arxiv.org/html/2508.00031v2  
11. Confucius Code Agent — https://arxiv.org/html/2512.10398v1  
12. HybridLLM — https://arxiv.org/abs/2404.14618  
13. RouteLLM — https://arxiv.org/abs/2406.18665  
14. RouterBench — https://arxiv.org/abs/2403.12031  
15. CE-CoLLM — https://arxiv.org/html/2411.02829  
16. Edge SLM survey — https://arxiv.org/html/2507.16731  
17. LMCache — https://arxiv.org/pdf/2510.09665  
18. Oblivion — https://arxiv.org/html/2604.00131v2  
19. Human-like consolidation — https://arxiv.org/html/2404.00573v1  
20. From Spark to Fire — https://arxiv.org/html/2603.04474  
21. Routing collapse — https://arxiv.org/html/2602.03478  
22. HybridLLM cascade — https://arxiv.org/pdf/2409.13757  
23. PCA — https://himjoe.github.io/proof-carrying-answers/  
24. Vouch PAD-045 — https://github.com/vouch-protocol/vouch/blob/main/docs/disclosures/PAD-045-proof-of-non-hallucination-retrieval-anchoring.md  
25. neleus-db — https://github.com/auralshin/neleus-db  
26. RAG-Shield — https://github.com/SidereusHu/RAG-Shield  
27. Governance Envelopes — https://sanna.dev/papers/governance-envelopes.html  
28. Letta memory blocks — https://www.letta.com/blog/memory-blocks  
29. GitGuardian ggshield — https://github.com/GitGuardian/gg-shield  
30. Sourcegraph Cody OSS — https://sourcegraph.com/blog/open-sourcing-cody  
31. Continue.dev — https://www.continue.dev/  
32. XPack MCP marketplace — https://github.com/xpack-ai/XPack-MCP-Market  

---

*End of sweep. Track B · research_only · not a Track A promotion artifact.*
