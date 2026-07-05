# Paste Chart v1 — Antigravity Surface Prompt v2 (복붙용)

**선행:** Cursor 구조·IWS advice gate · local/prod verify exit0 · Tauri scaffold gate exit0  
**Cursor P0 (구조):** `ClinicianEncounterGoldPanel` · `PasteChartOmniBox` · `.paste-chart-v1` DOM frozen  
**이번 v2:** Paste Chart **surface polish** — chip row · SOAP/advice 2열 · omni textarea (CSS only)

**Local:** http://127.0.0.1:3010/clinician?panel=gold  
**Prod smoke:** `node projects/no1kmedi/scripts/verify-paste-chart-auto-local-v1.mjs`

---

## ━━━ 복붙 시작 ━━━

```
AG_TASK: MKM Paste Chart v1 — surface polish (CSS ONLY · v2)

Polish the clinician Paste Chart gold panel. Structure/DOM/API is frozen by Cursor.

=== SCOPE ===
- EDIT: projects/no1kmedi/src/app/globals.css ONLY
- REGION: existing `.paste-chart-v1` block (~line 3550+) — merge/polish, do not delete hooks
- Max ~180 lines net change
- NO .tsx / API / copy string / advice logic edits

=== STEP 1 — OPEN LIVE ===
A) Local: http://127.0.0.1:3010/clinician?panel=gold
B) After paste sample: chips (이름·생년·성별·CC) + 2-column SOAP | advice

=== TARGET (1440×900) ===
· Dark clinical surface (#0a1210 card on #0a1210 page) — calm, not chat-app
· Omni: large textarea, single primary CTA (teal #3d9b84), draft chips as ghost pills
· Results: 2-column grid — left SOAP slots (copy buttons visible), right advice cards
· Advice card: title badge + checklist; primary card subtle green border
· Patient chip row: readable contrast, dot separators, ok-state green

=== FROZEN DOM (do not rename/remove) ===
  .paste-chart-v1  .paste-chart-shell  .paste-chart-omni
  .pc-draft-chip-row  .pc-draft-chip  .patient-chip-row  .patient-chip
  .soap-panel  .soap-slot  .advice-panel  .copilot-card
  .btn-analyze  .paste-chart-advice-warning

=== BRAND TOKENS ===
--clinical-green: #3d9b84 · --surface: #0a1210 · --surface-card: #111a17
--text: #e2e8f0 · --accent-gold: #c5a057 · --border: rgba(61,155,132,0.22)

=== FORBIDDEN ===
- Track A / live trading / pricing popups
- "100% verified", zero-hallucination marketing
- Changing 2-column collapse breakpoint without mobile fallback
- Light theme swap (stay dark clinical)

=== OUTPUT ===
Line 1: AG_HANDOFF: globals.css paste-chart-v1 surface v2, no TSX

A) CSS diff (paste-chart-v1 block only)
B) Handoff table 6 rows (omni · chips · SOAP · advice · mobile · reduced-motion)
C) Gate self-check yes/no for frozen selectors above
```

## ━━━ 복붙 끝 ━━━

## reproduce

```text
Read: reports/paste_chart_antigravity_prompt_v2_surface.md
Brief: reports/paste_chart_antigravity_design_brief_v1.md
Cursor gate: node projects/no1kmedi/scripts/verify-paste-chart-auto-local-v1.mjs
Tauri gate: powershell -File scripts/Invoke-ClinicianPasteChartTauriAutoVerify_v1.ps1
```
