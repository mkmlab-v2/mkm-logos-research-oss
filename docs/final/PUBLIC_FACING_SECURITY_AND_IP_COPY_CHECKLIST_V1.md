# Public-facing security, IP, and copy checklist (v1.2)

**Status:** policy SSOT for **websites, landing pages, proposals, and static showroom** (not a runtime contract).  
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
- **Engineering cross-check (not legal sign-off):** reviewers may spot-check repo gates that mirror the same posture: `scripts/verify_p0_constitution_gate_paths.ps1` (includes bundle scripts), generation policy `docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json`, and `scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1` (`-DryRun` prints the `py` argv). This does **not** replace **`docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` RQ-009** (legal / pilot KPI freeze).
- **Lens/regime contract:** use fixed lens names (`사상`, `명리`, `성경/Logos`) and operational layers (`Macro`, `regime`) as in `AGENTS.md`; do not imply a single unified physical theory “completed” in marketing copy.

## 4) Repository hygiene

- Large binaries and one-off exports belong out of Git default scope per `AGENTS.md` remote publication rules; promote intentionally (`git add -f`) only when intended.

**Revision:** 2026-05-14 — v1.2; anchor list: Track C **§3.7.2** `(B)` ↔ this file **§3** Silver Tech cross-lock; §3 engineering cross-check bullet vs RQ-009 (pre-legal only). (v1.1 same day: §3 non-clinical mandate; v1 initial: 2026-05-05 — health/wellness KR guardrails pointer.)
