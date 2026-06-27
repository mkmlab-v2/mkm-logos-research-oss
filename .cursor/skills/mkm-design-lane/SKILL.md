---
name: mkm-design-lane
description: Design/Showroom lane — Lovable-style Cursor UI workflow (CSS token SSOT, anchor pinning, smoke lock-in). Use for no1kmedi Hub, jemaai showroom, mkmlife consumer portal UI, Trust Composition reference→token→gate, clinic LOI landing, or when user mentions Lovable concept, discover v3, or Design lane.
---

# MKM Design Lane — Lovable-style in Cursor

**Scope:** `projects/no1kmedi` Hub · jemaai showroom static · mkmlife consumer_portal_v1 embed.  
**NOT:** Track A KPI headlines · operator console · live trading · Hub LLM.

## Workflow (3 steps)

### 1. Taste guard — CSS variables SSOT

Do **not** add DesignSystem YAML to root `.cursorrules`. Pin tokens in:

| Surface | SSOT |
| --- | --- |
| Hub discover v3 | `projects/no1kmedi/src/app/globals.css` — `.universe-hub-page--discover-v3` (`--hub-bg` `#191919`, `--hub-surface` `#202020`, `--hub-border` `#2a2a2a`) |
| mkmlife hub embed | `projects/mkm/mkm-life/app/globals.css` — `body[data-hub-embed='1']` (same token values) |

Run in no1kmedi when touching tokens: `npm run check:design-tokens` (if script exists in package.json).

### 2. Anchor pinning — minimal diff

Edit **existing** shell files only unless the user explicitly requests a new route:

| Anchor | Role |
| --- | --- |
| `UnifiedUniverseShellV2.tsx` | 3-column grid, discover v3 class gate |
| `UniverseCenterAskV2.tsx` | Pill/capsule ask input |
| `UniverseSidebarV2.tsx` | Collapse + icon rail |
| `HubEvidenceInspectorV3.tsx` | Read-only artifact panel |
| `HubShellClient.tsx` | Path → layout flags |

**Never** invent `DiscoverMainPanel.tsx` or parallel shell copies.

Intent routing stays in `universeHubIntentRouterV2.ts` — **UI-only** changes.

### 3. Lock-in — pytest + live smoke

From repo root:

```powershell
py -m pytest tests/test_universe_hub_discover_v3_v1.py tests/test_check_mkm_universe_hub_shell_v2.py tests/test_mkmlife_hub_origin_v1.py tests/test_universe_hub_mkmlife_embed_v2.py -q
py scripts/smoke_universe_hub_live_v1.py
```

Optional persona: `powershell -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona DesignLane`

Exit **0** before claiming “design done”.

## Path flags (Hub)

| Flag | When |
| --- | --- |
| `discoverMinimal` | `/hub` home only |
| `hubLightChrome` | `/hub` and `/hub/*` spokes |
| `showInspector` | `/hub` + `/hub/logos` |
| `discoverV3` | `discoverMinimal && showInspector` |

## mkmlife embed (local pair)

1. `NEXT_PUBLIC_MKMLIFE_ORIGIN=http://localhost:3105` in `projects/no1kmedi/.env.local`
2. mkmlife on `:3105`, Hub on `:3010`
3. Dev auto-embed: `isMkmlifeEmbedEnabled()` when origin is localhost + `NODE_ENV=development`
4. Prod embed: `NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED=1` (human sign-off)

Bootstrap: `powershell -File scripts\Invoke-HubMkmlifeLocalDevPair_v1.ps1 -BootstrapEnv`

## Compliance

- Copy/IP: `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7
- No Track A **47.5%** / compression headline in Hub UI
- Inspector / Logos: always `[HYPO]` · `[NON_GATING]` where applicable
- `consumer_portal_v1` ≠ `operator_console_v1` — no sidebar merge

## 12AI ops framing (optional)

- **S:** Scope one line (which anchor files)
- **L:** Implement minimal diff
- **M:** pytest + smoke exit 0

MKM **4AI core** is domain/lens — not UI routing labels.

## Trust Composition (reference → token → gate)

**SSOT:** `docs/final/MKM_TRUST_COMPOSITION_DESIGN_PIPELINE_V1.md` · rule `@mkm-trust-composition-design-v1`

| Step | Action |
| --- | --- |
| Seed | `design_reference_seed_v1` + audience profile |
| Tokens | DTCG 3-layer JSON (not flat hex paste) |
| Gate | `Run-ClinicLoiLandingDesignChain_v1.ps1` exit 0 |

Clinic LOI reference impl: `reports/clinic_km_mmp_landing_tokens_v2.dtcg.json` · `frozen_deferred` · `send_gate: HOLD`.

## Related rules

- `.cursor/rules/design-lane.mdc`
- `.cursor/rules/mkm-trust-composition-design-v1.mdc`
- `.cursor/rules/mkm-browser-automation-v1.mdc` (Tier 2 smoke only)
