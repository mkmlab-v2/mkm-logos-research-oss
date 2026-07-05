# JEMA AI · Antigravity Design Prompt Packs v1

**Status:** draft for external visual tooling (Antigravity / Figma / v0). **Not** merged to production until Cursor anchor integration + gates exit 0.

**Audit SSOT:** `docs/final/artifacts/jemaai_design_audit_surface_map_v1_latest.json`

**Pack A inputs (Antigravity attach):**

- `docs/final/artifacts/jemaai_dtcg_tokens_proposed_v1.dtcg.json` — 3-layer skeleton + `antigravity_proposed_*` slots
- `docs/final/artifacts/jemaai_design_reference_seed_antigravity_v1.json` — Trust Composition seed
- Validate: `py scripts/check_jemaai_dtcg_proposed_v1.py`

**Compile order (mandatory):** Pack 0 → **Pack A** → Pack D → Pack B → Pack C

**KM Han Medicine extension (2026-07-05):** Pack A supplement → **Pack E** (national ask) → **Pack F** (clinician) → **Pack G** (hub clinical) — full copy-paste prompts: `reports/km_han_medicine_antigravity_ui_ux_prompt_v1.md`

---

## Pack 0 — Design audit (Cursor only; do not send to Antigravity)

Purpose: freeze surface map, token drift, dependency walls before any visual generation.

**Deliverable:** `jemaai_design_audit_surface_map_v1_latest.json` (done 2026-07-02).

**Key drift to respect in all packs:**

| Layer | Accent | Notes |
|-------|--------|-------|
| `:root` | `#3d9b84` clinical green | Figma token map SSOT |
| `.preset-stripe-linear` | `#5b8cff` SaaS blue | Live marketing home |
| Hub discover v3 light | `#2d7a68` + gold `#c5a057` | `/hub` cream `#faf7f2` |
| `.enterprise-page` | blue glow family | `/validation` `/safety` `/enterprise` |

---

## Pack A — Tokens (compile first)

### Role

Produce **DTCG-style token proposal** (primitive → semantic → component). Output JSON + short rationale — **no full `globals.css` rewrite**.

### Antigravity prompt (EN)

```
You are a design-system architect for JEMA AI (B2B trust infrastructure, not a generic chatbot landing).

CONTEXT (read-only SSOT):
- DTCG skeleton (fill null slots only): docs/final/artifacts/jemaai_dtcg_tokens_proposed_v1.dtcg.json
- Reference seed: docs/final/artifacts/jemaai_design_reference_seed_antigravity_v1.json
- Spacing/type primitives already exist: --space-xs through --space-2xl, --text-xs through --text-hero, --radius-sm/md/lg (8pt scale).
- Figma map: docs/final/artifacts/no1kmedi_figma_token_map_v1.json
- Current drift: :root clinical green #3d9b84 vs marketing preset blue #5b8cff — propose explicit semantic aliases, do not collapse.

TASK:
1. Propose DTCG JSON with 3 tiers: primitive, semantic, component.
2. Semantic colors MUST include separate roles:
   - color.trust.clinical (green family)
   - color.trust.saas (blue family, marketing + enterprise chrome)
   - color.trust.hub (cream surface + gold accent, discover v3 only)
3. Typography: max 3 weights (400/600/700). Tight hero tracking. No fourth display font.
4. Motion: subtle only (150–220ms). No parallax, no infinite chat metaphor animations.
5. 2026 SaaS trend: low-saturation surfaces, thin borders, dense trust strips, short proof rows — NOT glassmorphism overload.

OUTPUT FORMAT:
- Updated `jemaai_dtcg_tokens_proposed_v1.dtcg.json` (fill antigravity_proposed_* nulls only)
- Mapping table: semantic token → existing CSS var (reuse) OR new var name
- Max 1 page "do not" list

HARD CONSTRAINTS:
- Do NOT output a replacement globals.css file.
- Do NOT merge hub gold palette into enterprise or validation pages.
- Do NOT add gradient-heavy crypto/Web3 aesthetics.
```

### Antigravity prompt (KO)

```
JEMA AI(B2B 신뢰 인프라) 디자인 시스템 아키텍트로 동작하세요. 일반 챗봇 랜딩이 아닙니다.

SSOT(읽기 전용):
- DTCG 스켈레톤(null 슬롯만 채움): jemaai_dtcg_tokens_proposed_v1.dtcg.json
- 레퍼런스 시드: jemaai_design_reference_seed_antigravity_v1.json
- 8pt 스페이스·타입 스케일은 이미 globals.css :root에 존재합니다.
- Figma 맵: no1kmedi_figma_token_map_v1.json
- 드리프트: :root 임상 그린 #3d9b84 vs 마케팅 preset 블루 #5b8cff — semantic alias로 분리 제안, 합치지 마세요.

작업:
1. primitive → semantic → component 3층 DTCG JSON 제안
2. semantic color 역할 분리: trust.clinical / trust.saas / trust.hub
3. 타이포 weight 3개(400/600/700) 상한, 히어로 letter-spacing 타이트
4. 모션 최소(150–220ms), 패럴랙스·무한 채팅 연출 금지
5. 2026 SaaS: 낮은 채도 surface, 얇은 border, 짧은 증거 strip(Time-to-Trust)

산출물: proposed DTCG JSON + 기존 CSS var 매핑표 + 금지 목록 1페이지

금지: globals.css 통째 교체, hub 골드를 enterprise/validation에 합류, Web3 과다 그라데이션
```

### Pack A acceptance (Cursor)

- [ ] Every proposed semantic maps to existing `--space-*` / `--text-*` or documents **one** new var with rationale
- [ ] No single `--accent` that forces one hue across marketing + hub + enterprise
- [ ] `node scripts/check-design-tokens-smoke.mjs` still passes after Cursor applies minimal :root/preset diff
- [ ] `no1kmedi_figma_token_map_v1.json` updated only if commander approves

---

## Pack D — Trust pages (second; isolates Ring 0/1)

### Routes

`/safety` · `/validation` · `/enterprise` · `/engine` (redirect)

### Antigravity prompt (EN)

```
Design refresh for JEMA AI "trust surfaces" — enterprise chrome only.

PAGES:
- /safety — lane routing governance table (Ring 0). Dry regulatory tone. Table is the hero.
- /validation — Ring 1 engineering evidence. Metrics strip + reproducibility list. Neutral; no tradition marketing.
- /enterprise — JEMA OS v2 middleware story. Neuro → Symbolic → Human pipeline diagram (abstract, not neuroscience proof).

VISUAL SYSTEM:
- Reuse class family: enterprise-page, validation-page, safety-page
- Palette: dark navy/slate base + saas blue accent (#5b8cff family) — NOT hub cream/gold
- Components: eyebrow pills, metric strip, monospace artifact paths, badge row (analysis_only, HOLD)

UI METAPHOR (layout only):
- Neuro: input areas minimal
- Symbolic: badges, metrics, gate commands, tables
- Human: disclaimer blocks, CTA to contact/clinician — never auto-execution

COPY: do not invent text. Reference structure only; strings live in public-copy.json.

FORBIDDEN:
- Combining Sasang + Myeongri + Scripture + brain science in one section
- Investment return headlines, "guaranteed" language
- Replacing tables with marketing illustrations

OUTPUT: Figma frames or HTML mock per page + component spec (spacing tokens only). No Next.js repo dump.
```

### Pack D acceptance

- [ ] Visual parity across `/safety` `/validation` `/enterprise` (shared header nav pattern)
- [ ] `npm run check:marketing-copy` + fingerprint gate exit 0 on `public-copy.json`
- [ ] Live smoke: `/safety` 200, `/validation` 200 (after Cursor merge)
- [ ] Ring 1 `/validation` body has no C-SASANG / C-MYEONGRI / C-LOGOS marketing clusters

---

## Pack B — Hub discover v3

### Antigravity prompt (EN)

```
Design refresh for JEMA AI Universe Hub — discover v3 only (/hub).

ANCHOR FILES (do not duplicate):
- UnifiedUniverseShellV2.tsx — 3-column grid
- UniverseCenterAskV2.tsx — pill ask input (one sentence routing)
- UniverseSidebarV2.tsx — collapse rail
- HubEvidenceInspectorV3.tsx — read-only artifact panel

VISUAL:
- Light chrome: bg #faf7f2, surface #fff, ink #292524, accent #2d7a68, gold #c5a057 borders
- Time-to-Trust: ask bar dominant; inspector secondary; no infinite chat layout
- Pill shadow subtle; focus ring accessible

DO NOT:
- Change URL routing or intent chips logic
- Add Track A KPI numbers (47.5%, etc.)
- Merge clinician workspace UI into hub
- Dark-mode the entire hub unless separate frame labeled "optional dark explore"

OUTPUT: Figma component set aligned to existing class names (hub-pill-link, universe-hub-*). Wireframe + hi-fi for 1440 and 390 widths.
```

### Pack B acceptance

- [ ] `py -m pytest tests/test_universe_hub_discover_v3_v1.py tests/test_check_mkm_universe_hub_shell_v2.py -q`
- [ ] `py scripts/smoke_universe_hub_live_v1.py` (when live keys available)
- [ ] No new shell component files in repo

---

## Pack C — Marketing home (last)

### Antigravity prompt (EN)

```
Design refresh for JEMA AI classic marketing home (/, /home) — Ring 0 single anchor only.

POSITIONING (one anchor sentence only on hero):
"Assistive AI informed by Korean Sasang tradition — non-clinical."

STRUCTURE (existing sections — restyle only):
- Hero: 4 CTAs hierarchy (primary consumer, secondary clinician, tertiary contact, quaternary validation)
- Feature triad, governance flow (anonymized lens labels), #safety block with link to /safety
- FieldLensGovernanceFlow — keep non_gating badges

PRESET: preset-stripe-linear (blue accent family). Calm clinical dark bg — not template purple gradient spam.

2026 TREND:
- Narrow type scale, 8pt spacing, proof strip under hero (3 bullets max visible)
- Role cards with clear primary/ghost button weights

FORBIDDEN:
- Listing Myeongri, manseryeok, Scripture, brain science in hero
- "Unified multi-lens fusion engine" visual metaphor
- New page sections that duplicate /safety or /validation content

OUTPUT: Figma frames for hero + safety CTA section + mobile stack. No copy rewrites — Korean strings from public-copy.json placeholders OK as lorem pointing to SSOT.
```

### Pack C acceptance

- [ ] `npm run check:marketing-copy` exit 0
- [ ] `check-homepage-marketing-copy-wired_v1.mjs` pass
- [ ] Hero retains Layer B marker compatibility (HomeHeroSection.tsx)
- [ ] fingerprint gate on public-copy.json unchanged or stricter

---

## Global handoff to Cursor (after Antigravity)

1. Import only token diffs into `globals.css` scoped blocks — **max ~120 lines per pack**
2. Apply layout/CSS to anchor components only — no parallel trees
3. Run acceptance gates from audit JSON `acceptance_gates_global`
4. Deploy via `Deploy-No1kmediDestinyTarball_v1.ps1` only after `npm run build` local exit 0

---

## Pack E / F / G — KM Han Medicine (Antigravity · 2026-07-05)

**SSOT:** `reports/km_han_medicine_antigravity_ui_ux_prompt_v1.md` (Master Brief + 3 surface packs + Pack A `.km-ask-*` supplement + Cursor handoff gates)

| Pack | Surface | Cursor anchor |
|------|---------|---------------|
| E | `no1kmedi.com/ask` L0 | `NationalKmAskClient.tsx`, `.km-ask-*` |
| F | `clinic.no1kmedi.com/clinician` L4 | `MinimalClinicianShell`, `ClinicianCanonCitePanel`, Paste Chart v2 |
| G | `jema-ai.com/hub` clinical group | `UniverseSidebarV2`, `universeHubPluginsV2.ts` |

**Compile order (KM):** Pack A supplement → E → F → G → (then existing D → B → C if full site pass)

---

## Revision log

| Date | Change |
|------|--------|
| 2026-07-05 | Pack E/F/G KM Han Medicine — pointer to `reports/km_han_medicine_antigravity_ui_ux_prompt_v1.md` |
| 2026-07-02 | v1 initial — audit JSON + packs A–D EN/KO + acceptance |
