# MKM · AI 한의학 UI/UX — Antigravity 프롬프트 팩 v1

**generated_at_utc:** 2026-07-05  
**status:** `[HYPO]` design handoff — **Figma/HTML mock only** until Cursor merge + gate exit 0  
**meta_cognition_ssot:** `docs/final/artifacts/mkm_ai_han_medicine_concept_stack_v1_latest.json`  
**prior packs:** `docs/final/artifacts/jemaai_antigravity_design_prompt_packs_v1_latest.md` (Pack A→D→B→C 순서 유지)

**이번 팩 추가 순서:** Pack A (token gap) → **Pack E** (대국민 ask) → **Pack F** (clinician) → **Pack G** (hub clinical)

---

## 0. Antigravity에 먼저 붙일 컨텍스트 (Master Brief · KO)

```
# ROLE
You are a senior product designer for JEMA AI / MKM — B2B trust infrastructure + Korean medicine assist surfaces.
You design Figma frames or static HTML mocks ONLY. You do NOT rewrite Next.js, APIs, or copy SSOT JSON.

# NORTH STAR (meta-cognition)
Three orthogonal surfaces — users must NEVER feel "three ChatGPTs":
1) L0 CONSUMER — no1kmedi.com/ask (national KM reference Q&A, non-clinical)
2) L4 CLINICAL — clinic.no1kmedi.com/clinician (physician Paste Chart + CDS draft, human_only)
3) HUB ROUTER — jema-ai.com/hub (one-sentence routing, no hub LLM)

Design job: make LAYER + PROVENANCE visible (badges, trust strips, citation collapses).
NOT: prettier infinite chat bubbles.

# DUAL BRAND (do not collapse)
- MKM 한의학 = corpus/tier/canon (WHAT) — show as citations, chunk refs, [교육·문화]
- AI 한의학 = CDS/runtime/gates (HOW) — show as human confirm, HOLD, artifact-connected drafts

# BODY AXIS [HYPO] — 함억/두견
- Philosophy (함억제복 / 두견요둔) = collapsed read-only education tab ONLY
- FORBIDDEN: constitution labels, phenotyping UI, voice/rib/formant routing, "your type is 太陽"

# VISUAL FAMILIES (do not merge)
| Surface | Palette | Reference classes |
|---------|---------|-------------------|
| National ask | trust.clinical light | .km-ask-* (currently orphan hex — align to DTCG) |
| Clinician | dark clinical #0a1210 + #3d9b84 | .paste-chart-v1, .minimal-clinician-* |
| Hub discover | cream #faf7f2 + #2d7a68 + gold #c5a057 | .universe-hub-page--discover-v3 |

# ATTACH (read-only)
- jemaai_dtcg_tokens_proposed_v1.dtcg.json
- jemaai_design_reference_seed_antigravity_v1.json
- mkm_ai_han_medicine_concept_stack_v1_latest.json (layers L0–L7)
- PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md §3 (Silver / non-medical)

# OUTPUT CONTRACT
For each pack: Figma page OR single HTML file + component spec table (spacing tokens only).
Line 1 of reply: AG_HANDOFF: <pack-id> <deliverable> no-repo-dump
Korean UI strings: use placeholders pointing to SSOT — do not invent medical claims.

# GLOBAL FORBIDDEN
- Infinite chat as hero (no typing indicator loops, no "always-on assistant" mascot)
- Track A KPI (47.5%, 0.890), live trading, guaranteed cure
- Merging Logos/명리/Oracle into clinician hero
- Light-theme clinician + dark Paste Chart inconsistency without documented intent
- Replacing chunk_id citations with fake book page numbers
```

---

## Pack E — 대국민 한의학 Q&A (`no1kmedi.com/ask`)

**Cursor anchor (frozen structure — design skin only):**  
`NationalKmAskClient.tsx` · classes `.km-ask-app` … `.km-ask-footer` in `globals.css` (~14187+)

### Antigravity prompt (복붙)

```
AG_TASK: Pack E — National KM Ask UI (no1kmedi.com/ask) · Figma + CSS spec

GOAL
Reskin L0 consumer surface so it reads as "one-question reference" NOT generic health chatbot.
Align .km-ask-* to DTCG trust.clinical light (reuse #3d9b84 family, 8pt scale).

VIEWPORTS: 390×844 mobile first, 1440×900 desktop

=== INFORMATION ARCHITECTURE (keep order) ===
1. Header row
   - Logo mark 韓 in rounded square (clinical green gradient OK, subtle)
   - Title: "no1kmedi 한의학 AI" + subtitle line NEW: "JEMA AI · 대국민 참고 Q&A"
   - Nav pills: [한의사 모드 → clinic] [대화 지우기]
2. Layer badge strip (NEW, always visible under header)
   - Pill: "L0 · 참고용 · 진단·처방 대체 아님"
   - Muted one line: Time-to-Trust — answers are educational context only
3. Disclaimer gate (first visit) — existing copy structure, improve typography hierarchy
4. Main thread OR empty state
   - Empty: 4 starter chips (existing prompts) — style as ghost pills, max 2 lines each
   - Thread: user bubble right, assistant bubble left
   - UNDER EACH assistant bubble (NEW): Provenance strip component "KmAskProvenanceStrip"
     · Default honest state: "참고·교육용 · 원전 자동 cite 미연결 · 한의사 진료는 clinic에서"
     · Optional future state (wireframe only): "원전 1건 · [교육]" collapsed details
5. Composer: textarea 2 rows + primary "질문하기"
6. Footer: disclaimer repeat + link "인증 한의사 모드"

=== NEW COMPONENTS TO DESIGN ===
A) KmAskProvenanceStrip — compact, Logos CitationLockStrip pattern (details/summary), not a second chat
B) KmAskLayerBadge — 11px uppercase tracking, border only, no alarm red
C) Soft session hint (NEW, non-blocking): after 5 turns show slim banner
   "주제를 정리할까요? · 새 대화" — NOT modal, NOT guilt trip

=== VISUAL ===
- Background: #f7f8fa or semantic surface.trust.clinical.muted
- Primary: #3d9b84 (match :root clinical green)
- Typography: existing --text-xs/sm/base; max weight 600 for titles
- Border radius: 10–12px cards, 999px pills
- NO: purple gradients, floating FAB, avatar illustrations, "AI doctor" iconography

=== COPY (structure only — do not rewrite legal) ===
- Keep existing disclaimer semantics from national-km-ask-v1
- Subtitle must clarify relationship: JEMA AI brand + no1kmedi host

=== FORBIDDEN ===
- Constitution / four-type diagnosis visuals
- mkmlife MAI / fortune styling
- Hub cream/gold palette on this page
- Hiding disclaimer below fold on mobile

=== OUTPUT ===
1. Figma: Mobile + Desktop frames named "PackE-NationalAsk"
2. Spec table: each .km-ask-* class → token mapping (max 25 rows)
3. HTML mock optional (single file, no JS) for ProvenanceStrip + LayerBadge only
AG_HANDOFF: Pack E Figma + spec, no TSX
```

---

## Pack F — 한의사 Clinician (`clinic.no1kmedi.com/clinician`)

**Cursor anchors:**  
`MinimalClinicianShell.tsx` · `ClinicianEncounterGoldPanel.tsx` · `ClinicianCanonCitePanel.tsx`  
CSS: `.minimal-clinician-*` · `.paste-chart-v1` · `.clinician-canon-cite-*`

### Antigravity prompt (복북)

```
AG_TASK: Pack F — Clinician KM Assist UI · Chat-First shallow + CDS cite spine · Figma

GOAL
Physician workspace: Paste Chart is PRIMARY shallow path; CDS/cite is DEEP on demand.
Fix meta-cognition collapse: one workspace, visible layers, cite attached to SOAP not floating orphan.

VIEWPORTS: 1440×900 (Paste Chart default), 390×844 (drawer nav + sheet cite)

=== SHALLOW DEFAULT (first paint) ===
Top trust strip (NEW, visible — replace hidden trust marker concept):
  "CDSS 보조 · human_only · artifact 연결 시 초안 · [HYPO] 참고"
  Right link: "안전·고지"

Primary nav REDUCE to 2 visible + overflow:
  [Paste Chart] [대화]  ··· 더보기 → 진료분석, 환자·설정, 번들, 안전

=== PASTE CHART (panel=gold) — polish v3 on v2 surface ===
Keep frozen DOM from paste_chart_antigravity_prompt_v2_surface.md:
  .paste-chart-v1 .paste-chart-omni .pc-draft-chip-row .soap-panel .advice-panel
Dark clinical tokens:
  --surface #0a1210 · --clinical-green #3d9b84 · --accent-gold #c5a057

ADD inside SOAP/advice results area:
  "CanonEvidenceBlock" (NEW component design)
  - Header: "원전 근거 (n)" + badge [교육·문화]
  - Rows: section_label + 2-line excerpt (human readable FIRST)
  - Footer monospace: IJEOMA-EDT-* chunk_id (secondary, 11px)
  - Collapsed by default; expands to 3 items max
  - Empty state: "CDS envelope 연결 후 표시 · 또는 원전 검색"

=== CANON CITE — move from floating pill to SHEET ===
Replace bottom-right fixed panel pattern with:
  - Sticky footer button: "원전 참고 [교육·문화]"
  - Opens bottom sheet (mobile) / right drawer 360px (desktop)
  - Search field + prefill hint line: "CDS·주증상 기반 제안: …"
  - Philosophy block (collapsed details): "[HYPO] 함억·두견 — 체질·처방 트리거 아님" (2 sentences max placeholder)

=== CDS / GRAPH (deep — secondary) ===
When "진료 분석" selected: keep existing canvas but add top breadcrumb:
  "Deep · CDS 초안 · 원장 확정 필요"

=== PRO EMAIL GATE ===
Design unlock card BEFORE block screen:
  3 bullets: Paste LLM extract · CDSS draft · 환자 번들 preview
  CTA: email field + "권한 확인" — calm, not paywall aggressive

=== REFERENCE PATTERN ===
Logos LogosResearchAskCitationLockStrip — compact details/summary for citations
Trust Composition: HOLD badge, audit id placeholder, no fake checkmarks

=== FORBIDDEN ===
- Consumer fortune / PersonaDiary cute palette
- 4AI personality avatars as diagnosis
- EMR auto-write animation
- Constitution classifier UI
- Voice waveform / rib angle inputs

=== OUTPUT ===
1. Figma page "PackF-Clinician" — 4 frames: Paste success, Paste empty, Cite sheet open, Pro gate
2. Component spec: CanonEvidenceBlock, TrustStripClinician, NavShallowOverflow
3. Redline: mobile sheet vs desktop drawer breakpoints
AG_HANDOFF: Pack F Figma + component spec, no TSX
```

---

## Pack G — Hub 임상·한의사 그룹 (`jema-ai.com/hub`)

**Cursor anchors:**  
`UniverseSidebarV2.tsx` · `UniverseCenterAskV2.tsx` · `universeHubPluginsV2.ts` (clinical navGroup)

### Antigravity prompt (복북)

```
AG_TASK: Pack G — Hub clinical lane UX · sidebar + handoff · Figma 1440 + 390

GOAL
Hub stays router NOT product buffet. Clinical group visually separated from B-track observatories.

=== SIDEBAR (discover v3 light chrome) ===
Group order: Discover · B2B · **임상·한의사** · 소비자·관측 · Ops(hidden)

Group "임상·한의사" (2 items only, always expanded):
  1. 대국민 한의학 AI → external no1kmedi.com/ask
     Badge: L0 · 참고
  2. 한의사 보조 → external clinic.no1kmedi.com/clinician
     Badge: L4 · human_only

Group "소비자·관측" — COLLAPSED by default on mobile:
  Items: Logos, 명리, Oracle, PersonaDiary, …
  Each item: small pill [HYPO] or [research_only] — color muted vs clinical green

=== EXTERNAL LINK HANDOFF (NEW) ===
When user clicks clinical external links, design modal/toast (wireframe):
  "임상 레인으로 이동합니다 · no1kmedi/clinic · 허브 LLM 없음"
  [계속] [취소]
  (Cursor may implement as subtle banner — design both)

=== CENTER ASK (unchanged logic) ===
Intent chips row: keep 6 chips but visual weight:
  Primary chips: 라이프·원퀘스천, **한의사 보조**
  Secondary: 관측·리서치, B2B, …
Clinician chip MUST match sidebar target (clinic.no1kmedi.com) — annotate in spec

=== HIDE from general users (partner fold) ===
Coordinate envelope / LTM pointer panel — move to "심사·파트너 30초" accordion only
Design collapsed state default for public; expanded for reviewer mock frame

=== VISUAL ===
Reuse hub tokens: bg #faf7f2, accent #2d7a68, gold #c5a057 borders
Clinical badges use #3d9b84 outline — NOT hub gold fill (lane separation)

=== FORBIDDEN ===
- Clinician SOAP UI embedded in hub main canvas
- Mixing compression KPIs with KM copy
- 12 equal-weight sidebar icons without grouping

=== OUTPUT ===
Figma "PackG-HubClinical" — sidebar expanded/collapsed, handoff modal, mobile rail
Spec: badge taxonomy table (L0/L4/[HYPO]/[NON_GATING])
AG_HANDOFF: Pack G Figma + badge taxonomy, no TSX
```

---

## Pack A 보강 — `.km-ask-*` 토큰 흡수 (Antigravity · 짧게)

```
AG_TASK: Pack A supplement — map .km-ask-* orphan hex to DTCG trust.clinical

Input: globals.css .km-ask-app block (hardcoded #f7f8fa, #3d9b84, etc.)
Output: 8 semantic tokens only:
  color.kmAsk.surface / .surfaceElevated / .border / .text / .textMuted
  color.kmAsk.primary / .primaryHover
  component.kmAsk.bubbleUser / .bubbleAssistant
Map each to existing --space-* / --radius-* where possible.
Do NOT merge kmAsk into trust.hub (cream/gold).
AG_HANDOFF: DTCG JSON delta + mapping table
```

---

## Cursor IDE 핸드오프 (Antigravity 산출물 받은 후)

Antigravity는 **Figma/HTML/spec만** 남기고, Cursor가 아래만 merge:

| Pack | Cursor merge 허용 | Gate |
|------|-------------------|------|
| E | `globals.css` `.km-ask-*` + new presentational components in `NationalKmAskClient.tsx` | `probe_no1kmedi_national_km_ask_live_v1.py` exit 0 |
| F | CSS + `ClinicianCanonCitePanel` sheet layout · `CanonEvidenceBlock.tsx` NEW | `probe_clinician_canon_cite_live_v1.py` exit 0 |
| G | `globals.css` `.universe-hub-*` badge classes only | `pytest test_no1kmedi_hub_clinical_p2_v1.py` |

**금지:** Antigravity가 `.tsx` logic·API·`public-copy.json` 법무 문구 직접 수정

**Deploy:** `Deploy-No1kmediDestinyTarball_v1.ps1` after local `npm run build` exit 0

---

## reproduce

```text
Read: reports/km_han_medicine_antigravity_ui_ux_prompt_v1.md
Prior: docs/final/artifacts/jemaai_antigravity_design_prompt_packs_v1_latest.md
Meta: docs/final/artifacts/mkm_ai_han_medicine_concept_stack_v1_latest.json
Paste Chart surface ref: reports/paste_chart_antigravity_prompt_v2_surface.md
```
