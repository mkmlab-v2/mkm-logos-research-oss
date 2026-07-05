# KM Han Medicine UI/UX — Antigravity Handoff Pack

Design-only handoff bundle for **no1kmedi.com/ask**, **clinic.no1kmedi.com/clinician**, and **jema-ai.com/hub** clinical lane.

**Status:** `[HYPO]` — Figma/HTML mock until Cursor merge + gate exit 0.

## Contents

| Path | Role |
|------|------|
| `prompts/` | Antigravity copy-paste packs (Master Brief + Pack A supplement + E/F/G) |
| `ssot/` | DTCG tokens, design seed, concept stack, global Antigravity pack index |
| `handoff/` | Cursor IDE transition guide |
| `mocks/` | Drop Antigravity Figma exports / HTML mocks here (empty until AG delivers) |
| `cursor/` | Merge checklist + gate commands |

## Quick start

1. Read `SETUP.md`
2. Open `prompts/km_han_medicine_antigravity_ui_ux_prompt_v1.md` — run packs in order: **A supplement → E → F → G**
3. Place AG deliverables under `mocks/` (e.g. `PackE-NationalAsk.fig`, `PackF-Clinician.html`)
4. Cursor merge: follow `cursor/MERGE_CHECKLIST.md` — **CSS + presentational TSX only**

## Rebuild ZIP (from repo root)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Prepare-KmHanMedicineBundle_v1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Build-KmHanMedicineUiUxHandoffZip_v1.ps1
# or one shot:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Prepare-KmHanMedicineBundle_v1.ps1 -BuildZip
```

Output: `reports/km_han_medicine_ui_ux_v1.zip`

## Forbidden (Antigravity + early Cursor)

- 체질 확정 UI, 함억/두견→처방 트리거
- Track A KPI, live trading copy
- Hub cream/gold on clinician dark shell without documented intent
- TSX logic, API routes, `public-copy.json` legal strings

## Live gates (after Cursor merge)

```text
py scripts/probe_no1kmedi_national_km_ask_live_v1.py
py scripts/probe_clinician_canon_cite_live_v1.py
py -m pytest tests/test_no1kmedi_hub_clinical_p2_v1.py -q
```
