# Public-facing security, IP, and copy checklist (v1.6)

**Status:** policy SSOT for **websites, landing pages, proposals, and static showroom** (not a runtime contract). **v1.6** adds §3 **Track C news ingest — dual-rail posture** (B2B observability vs showroom topology; not a news portal or trade-picking feed). **v1.5** adds §3 **GTM 인접(메타-뉴스·확률 스냅샷)** 면책·비단정 불릿. **v1.4** adds §3 **Trust Visualization v0** copy posture (artifact-bound; `[NON_GATING]`; CONSTITUTION + CI SSOT pointers). **v1.3** adds Silver SSOT freeze policy (pilot KPI / final liability deferred; structural human gates per Track C §3.7.2 `(B)`).  
**Supersedes:** nothing; align with repo SSOT below.

**Anchor documents (read in this order for full rules):**

- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — implementation facts; agents must not claim “shipped” from copy alone.
- `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` — commercialization guardrails (e.g. core-theory protection, public vs private field boundaries, legal copy baselines); **§3.7.2** Silver Tech draft requires **§3** of this checklist in `(B)`.
- `docs/final/TRACK_C_TOPOLOGY_RADAR_SHOWROOM_BLUEPRINT_V1.md` — Topology Radar / Resonance 쇼룸 **1p 청사진**(DRAFT; §3.6 확장; 대외 시 `PUBLIC_FACING`·법무 검토 병행).
- `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md` — public billboard vs private cockpit; `public-event.v1` semantics; **§4.4 Topology Radar** 슬롯(읽기 전용 스냅샷).
- `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md` — outward-facing engineering vocabulary for Myeongri; **do not rename code identifiers**.
- `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` — section 10–11: mkmlife.com / no1kmedi UI badges, disclaimer IDs, product UX locks; deployment paths Hostinger/VPS are in sections 1–9 of that file (do not mix with jema12 deploy runbooks).
- `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` — section 1.1 (배치·톤), **1.1b** (jema-ai.com → jemaai/mkmlife/a-codeai **CTA 라벨 초안**).
- `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md` — jema-ai.com 배포·미확정 금지; **§4.1** CTA는 `MKM_DOMAIN_PORTFOLIO` 1.1b와 정합.
- `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md` — 건강·웰빙·설문·체질 표현 블랙/그레이/화이트 초안 (KR 상용 카피; 법무 검토 전제).

## 1) Security (channels: web, PDF, decks, email)

- No API keys, webhook URLs, bearer tokens, internal hostnames, DPAPI paths, or `.env` excerpts in public artifacts.
- Prefer **artifact-bound** claims: link or cite stored JSON/report paths only where intentionally published; otherwise describe capability at a **high level**.
- **Operational realism:** do not promise “real-time,” “zero latency,” or “live execution” unless the published SPEC and deployed gateway explicitly define latency, staleness, and disclaimers.

## 2) IP and theory boundaries

- **Invisible core, visible evidence:** public surfaces show **outputs and governance posture**, not proprietary formulas, full pipelines, or unreleased model internals.
- Do not paste **unreleased paper mappings, hypothesis inventories, or B-track-only JSONL** into customer-facing documents without review.
- Track C packaging rules (access control, watermarking, separation of Model-as-a-Service) stay authoritative for commercial assets — see the Track C plan.

## 3) Copy and compliance tone (minimum bar)

- Avoid absolute claims: “guaranteed returns,” “regulatory risk zero,” “clinical proof,” “always profitable.”
- Investment-adjacent surfaces: retain baseline disclaimers consistent with `TRACK_C_IP_BUSINESS_PLAN` (e.g. not investment advice; no guarantee of returns; final decisions with operators).
- Health-adjacent surfaces: avoid diagnostic/treatment/prescription language unless separately validated for that jurisdiction and product; 용어 표는 `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md`.
- **Silver Tech / senior-care surfaces:** mandatory **non-clinical, non-emergency** framing in copy: daily logs and emotional summaries are **observational only** and do **not** replace medical diagnosis. Do **not** depict or promise automated medical prescribing or emergency dispatch **without explicit human verification** and product/legal clearance for that jurisdiction. Mechanically align with `patient_care_bundle` anti–short-circuit posture (`docs/final/schemas/patient_care_bundle_v1.schema.json`; Track C draft `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2).
- **Engineering cross-check (not legal sign-off):** reviewers may spot-check repo gates that mirror the same posture: `scripts/verify_p0_constitution_gate_paths.ps1` (includes bundle scripts), generation policy `docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json`, and `scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1` (`-DryRun` prints the `py` argv). This does **not** replace **`docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` RQ-009** (legal / pilot KPI freeze). **Internal counsel handoff pack (draft, not final public copy):** `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md`.
- **Silver Tech — SSOT freeze policy (commander 2026-05-15):** Do **not** embed pilot KPI counts, margin targets, or **final** jurisdiction-specific liability copy into this checklist (or other repo “truth” pages) until **pilot evidence + legal review**; keep those in internal R&D annexes and hypothesis-tagged research files (e.g. `docs/research/silver_tech_cogs_unit_economics_template_v1.md`). **Pre-promotion step order (internal ops only):** use that file’s section **「동결 게이트 (RQ-009 · 팀 내부만)」** — do **not** duplicate the step table in customer-facing pages; Track C §3.7.2 `(C)` keeps policy/deferral only. **Structural** safety: no solo autopilot for **sensitive external actions** (payments, calls, account changes) — align with `TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.7.2 `(B)` (human-in-the-loop gates: notify, approve, block, audit log).
- **Trust Visualization v0 (static showroom + STT audit slice):** Treat as **read-only demo** and **artifact-bound** claims only — paths, schema, pytest trio, CI step, and local bundle slice are SSOT in `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (Visualization v0 bullets) and `.github/workflows/dual-regime-integrity.yml`. Logos / biblical framing in that slice stays **`[NON_GATING]`** (explanatory, not a clinical or trading trigger). Same §3 bars: no pilot KPI / margin / final liability numbers in customer-facing copy; no clinical or emergency automation promises.
- **Lens/regime contract:** use fixed lens names (`사상`, `명리`, `성경/Logos`) and operational layers (`Macro`, `regime`) as in `AGENTS.md`; do not imply a single unified physical theory “completed” in marketing copy.
- **GTM — meta-news / probability snapshot (B-rail adjacent):** Any `general_prophecy`-style or “meta-news” surface must carry the same **Creative-Lock / observation-only** posture as research artifacts: **no** “100% success,” **no** substitution for expert or clinical judgment, **no** implied auto-trading or auto-care. Present **p-values and refresh timestamps** as **hypothesis-tier observability**, not endorsements. Korean/English one-liners may mirror `docs/final/artifacts/general_prophecy_brief_latest.md` footer and `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md` until counsel replaces them.
- **Track C — news ingest (dual-rail, not a content portal):** Do **not** market MKM as a **headline feed**, engagement-chasing “infinite scroll” media, or **trade-picking / guaranteed move** copy. Align with `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` **section 3.5** (enterprise **regime pressure + event alerts**; value = measurable ops KPIs like alert timeliness / report SLA — **not** buy/sell instructions) and **section 3.6** (showroom: raw disclosure/news text → **topology / resonance-style metrics + reproducible artifact links** — **not** deterministic price answers). B-track, Pre-News shadow, and related JSONL paths are **observation / research tier** in public wording unless a separate product SSOT explicitly promotes them; never imply **automatic live-trading triggers** from these surfaces. Domain split (hub vs `jemaai.cloud` showroom): `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` section **1.1b** and `projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md`.
- **Non-medical reinforcement (Silver + general public):** Observational logs, stress metaphors (e.g. M31-style), and lens narratives are **wellness-adjacent copy only** unless the product is separately cleared for regulated claims in that jurisdiction — align with `MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md` and `patient_care_bundle` short-circuit rules in §3 Silver bullets above.

## 4) Repository hygiene

- Large binaries and one-off exports belong out of Git default scope per `AGENTS.md` remote publication rules; promote intentionally (`git add -f`) only when intended.

**Revision:** 2026-05-15 — **v1.6** §3 Track C news ingest dual-rail (3.5 / 3.6 alignment; no portal or auto-trading implication). **v1.5** §3 GTM 인접(메타-뉴스·확률 스냅샷) 비단정·Creative-Lock·비의료 보강 불릿. (2026-05-17 — §3 Silver: internal **동결 게이트** step order lives only in `docs/research/silver_tech_cogs_unit_economics_template_v1.md` (KR heading); no duplicate step tables in public copy (Track C §3.7.2 `(C)` policy-only).) (2026-05-16 — §3 RQ-009 내부 면책 패킷 포인터 `docs/final/artifacts/silver_tech_legal_disclaimer_draft_v1.md`.) (동일일 §3 Trust Visualization v0 bullet.) (2026-05-15 — v1.3 Silver freeze.) (v1.2 2026-05-14 … v1 2026-05-05.)
