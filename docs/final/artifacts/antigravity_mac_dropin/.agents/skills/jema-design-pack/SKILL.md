---
name: jema-design-pack
description: Run when commander asks for JEMA/no1kmedi/KM UI Pack A–G or L-Ask visual draft on Antigravity. Design-only; no production merge.
---

# JEMA Design Pack (Antigravity)

## When

- Pack A tokens, B Hub, C marketing, D trust pages, E–G KM surfaces, or L-Ask visual batch.
- User attaches DTCG JSON, reference seed, or Master Brief.

## Steps

1. Confirm **one Pack** and surface; refuse multi-surface rewrites in one shot.
2. Read attached SSOT only (DTCG / seed / Pack prompt / public-copy placeholders).
3. Produce allowed outputs only:
   - fill `antigravity_proposed_*` nulls, **or**
   - mock HTML under `mocks/Pack*/`, **or**
   - Figma frames + scoped CSS patch
4. Preserve anchor component names and CSS class prefixes (`universe-hub-*`, `hub-pill-link`, `.km-ask-*`, ask frozen classes).
5. Append `CURSOR_HANDOFF` footer from `.agents/AGENTS.md`.

## Hard stop

If asked to change routers, gates, `.env`, or claim “merged to production” — stop and redirect to PC Cursor.
