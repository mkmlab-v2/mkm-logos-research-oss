# Antigravity Mac drop-in — install (v1)

**Generated for:** mkmlab MacBook · design satellite  
**PC SSOT:** this folder under `C:\workspace\docs\final\artifacts\antigravity_mac_dropin\`  
**Pointer:** `docs/final/artifacts/mkm_antigravity_mac_agents_v1_latest.md`

## What this is

Ready-to-copy Antigravity customizations:

| Path | Purpose |
|------|---------|
| `.agents/AGENTS.md` | Workspace rules (design-only) |
| `.agents/skills/jema-design-pack/SKILL.md` | Pack workflow skill |

**Not included on purpose:** full `.cursorrules`, Fact-Lock, MCP, Windows scripts.

## Mac install (thin design repo)

1. On Mac, clone or open a **thin** design folder (e.g. `km_han_medicine_ui_ux` or a `design-surface` mirror). Do **not** open the full monorepo in Antigravity.
2. Copy this drop-in into that folder root:

```bash
# from a USB / Tailscale sync / git sparse checkout of this artifacts path
cp -R antigravity_mac_dropin/.agents /path/to/thin-design-root/
```

3. Optional global (all Antigravity projects) — paste only the **Never** + role lines into:

`/Users/mkmlab/.gemini/config/AGENTS.md`

4. Attach Pack inputs when chatting (from PC sync or thin clone):
   - `jemaai_antigravity_design_prompt_packs_v1_latest.md`
   - `jemaai_dtcg_tokens_proposed_v1.dtcg.json`
   - `jemaai_design_reference_seed_antigravity_v1.json`
5. After drafts: hand off to **PC Cursor** for scoped CSS merge + gates.

## GitHub (optional)

Prefer a **design-only** repo or sparse tree: mocks + DTCG + Pack MD + this `.agents/`.  
Never push `.env`, secrets, patient artifacts, or full `scripts/` health chains.

## Device rules (2014 Intel Mac)

- Antigravity **occasional**; AI Studio = daily mocks.
- One agent; no Antigravity + Xcode + heavy Chrome together.
- No second Cursor login on Mac (PC Cursor only).

## Verify (human)

- [ ] Antigravity lists workspace rules from `.agents/AGENTS.md`
- [ ] Skill `jema-design-pack` appears under skills
- [ ] First Pack run returns `CURSOR_HANDOFF` footer
