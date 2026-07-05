# SETUP — KM Han Medicine UI/UX Handoff

## Prerequisites

- Antigravity (or Figma) for visual mock generation
- Cursor IDE with repo `C:\workspace` (no1kmedi app lives in `projects/no1kmedi`)

## Pack compile order

```
Pack 0 (Cursor audit only — do not send to AG)
  ↓
Pack A supplement (.km-ask-* → DTCG trust.clinical)
  ↓
Pack E — no1kmedi.com/ask (L0 national KM)
  ↓
Pack F — clinic.no1kmedi.com/clinician (Paste Chart + cite spine)
  ↓
Pack G — jema-ai.com/hub clinical group
  ↓
(Optional full site) Pack D → B → C — see ssot/jemaai_antigravity_design_prompt_packs_v1_latest.md
```

## Antigravity session

1. Attach all files under `ssot/` plus `prompts/paste_chart_antigravity_prompt_v2_surface.md`
2. Paste **Master Brief** from `prompts/km_han_medicine_antigravity_ui_ux_prompt_v1.md` §0
3. Run Pack A supplement, then E, F, G (one pack per session recommended)
4. Export to `mocks/`:
   - `PackE-NationalAsk/` — mobile + desktop frames
   - `PackF-Clinician/` — Paste, cite sheet, pro gate
   - `PackG-HubClinical/` — sidebar + handoff modal

## Cursor merge scope (after mock approval)

| Pack | Allowed files | Gate |
|------|---------------|------|
| E | `globals.css` `.km-ask-*`, `NationalKmAskClient.tsx` presentational | `probe_no1kmedi_national_km_ask_live_v1.py` |
| F | clinician CSS, `ClinicianCanonCitePanel.tsx`, new `CanonEvidenceBlock.tsx` | `probe_clinician_canon_cite_live_v1.py` |
| G | hub badge CSS, sidebar labels | `test_no1kmedi_hub_clinical_p2_v1.py` |

Deploy: `powershell -File scripts\Deploy-No1kmediDestinyTarball_v1.ps1` after local `npm run build` exit 0.

## SSOT paths (repo canonical)

All copies in this bundle mirror:

- `docs/final/artifacts/jemaai_dtcg_tokens_proposed_v1.dtcg.json`
- `docs/final/artifacts/jemaai_design_reference_seed_antigravity_v1.json`
- `docs/final/artifacts/mkm_ai_han_medicine_concept_stack_v1_latest.json`
- `docs/final/artifacts/jemaai_antigravity_design_prompt_packs_v1_latest.md`

Do **not** use `c:\workspace\artifacts\` — that path is not the repo SSOT.
