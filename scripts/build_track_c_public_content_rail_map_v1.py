#!/usr/bin/env python3
"""Track C public content rail map (design-only) — no auto-publish hooks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/track_c_public_content_rail_map_v1_latest.md"


def main() -> int:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = f"""# Track C — Public Content Rail Map (Design Only)

- **generated_at_utc:** `{generated}`
- **status:** `DESIGN_ONLY` — no scheduler, no YouTube upload, no external send
- **boundary:** B-track `[HYPO]` · compression bench ≠ trading edge · `ready_for_external_send` false until legal per surface

## Rails

| Surface | Role | SSOT copy / artifact | Auto-publish |
|---------|------|----------------------|--------------|
| **YouTube** | Observation + disclaimer; no return claims | `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7 · metaphor guardrail | **OFF** (`MKM_YouTube_Publish_Pipeline` disabled) |
| **Blog / newsletter** | Artifact-bound posts (JSON path + limits) | `compression_enterprise_executive_summary_v1.md` Plugin § · `track_c_combined_b2b_offer_onepager` Part C | Manual only |
| **B2B / IR** | Internal meeting pack | `track_c_b2b_meeting_pack_index_v1_latest.md` · compression appendix | `ready_for_internal_meeting` gate only |
| **Inter-agent Draft (RQ-019)** | Measured agent message rail | `mkm_inter_agent_ir_snippet_v1.md` + counsel ref `LC-2026-05-19-RQ019-CLEARED` | Draft disclaimer required on every page |

## Forbidden (all surfaces)

- Compression saving % as trading alpha or LG-style guarantee
- Prophecy hit rate / shadow PnL in public copy (90-day ops freeze)
- Neuroscience proof, 100% lossless, "TCP/IP of AI" liability phrases

## Next implementation (when commander approves)

1. Content template repo paths only (no API keys in repo)
2. Human review queue before any `Push-GitHub-Explicit` or CDN sync
3. Separate chat for prophecy metrics — never merged into compression IR slides

## Evidence pointers

- Track C plan: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`
- Promotion gates (B-track): `docs/final/artifacts/prophecy_promotion_gates_v1_latest.json`
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8", newline="\n")
    meta = OUT.with_suffix(".meta.json")
    meta.write_text(
        json.dumps(
            {
                "schema": "track_c_public_content_rail_map_v1",
                "generated_at_utc": generated,
                "research_only": True,
                "auto_publish": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
