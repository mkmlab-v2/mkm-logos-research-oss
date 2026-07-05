# Cursor merge checklist — KM Han Medicine UI/UX

Use after commander approves Antigravity mocks in `mocks/`.

## Pre-merge

- [ ] Mock matches Pack E/F/G spec (layer badges, provenance strip, cite sheet — not infinite chat)
- [ ] No forbidden items (체질 UI, Track A KPI, palette collapse)
- [ ] Token mapping table from Pack A supplement reviewed

## Per-pack merge

### Pack E — National ask

- [ ] `.km-ask-*` uses DTCG `trust.clinical` tokens (no orphan hex unless mapped)
- [ ] `KmAskProvenanceStrip` + `KmAskLayerBadge` added (presentational)
- [ ] Disclaimer + footer unchanged semantically
- [ ] `py scripts/probe_no1kmedi_national_km_ask_live_v1.py` → `all_ok: true`

### Pack F — Clinician

- [ ] Trust strip visible (not hidden marker only)
- [ ] Nav shallow: 2 primary + overflow
- [ ] `CanonEvidenceBlock` in SOAP/advice area (excerpt before chunk_id)
- [ ] Cite panel → bottom sheet / drawer (not orphan floating pill)
- [ ] `py scripts/probe_clinician_canon_cite_live_v1.py` → `all_ok: true`

### Pack G — Hub

- [ ] Clinical group: 2 items, L0/L4 badges
- [ ] Consumer group collapsed default on mobile wireframe intent
- [ ] Clinician chip URL = `clinic.no1kmedi.com/clinician`
- [ ] `py -m pytest tests/test_no1kmedi_hub_clinical_p2_v1.py -q` pass

## Post-merge

- [ ] `npm run build` in `projects/no1kmedi` exit 0
- [ ] Optional: `py scripts/check_no1kmedi_hub_design_gate_v1.py` if hub CSS touched
- [ ] Deploy tarball if live verify needed
- [ ] PR: design-only diff; link mock paths under `mocks/`
