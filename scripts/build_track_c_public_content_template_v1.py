#!/usr/bin/env python3
"""Draft YouTube/blog copy shells (manual publish only). DESIGN_ONLY."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/track_c_public_content_template_v1_latest.md"


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = f"""# Track C — Public Content Templates (Draft · Manual Publish)

- **generated_at_utc:** `{ts}`
- **status:** `DESIGN_ONLY` — no API keys, no scheduler, no auto-upload

## YouTube (short, observation-only)

**Title (KO):** MKM Track C — 거시·레짐 관측 브리핑 (매매 지시 아님)

**Description footer (paste always):**
> 본 영상은 연구·관측 목적이며 투자 자문·매매 지시가 아닙니다. 과거 지표는 미래 수익을 보장하지 않습니다.

**Pinned comment:** 아티팩트 경로는 내부 리포트 JSONL 기준이며, 수치는 `docs/final/artifacts/` 산출물과 함께 검증됩니다.

## Blog post (EN shell)

**Headline:** Governance-first macro risk posture — artifact-bound briefing

**Lead:** We publish structured scenario posture and alert metadata. This is not investment advice and does not include buy/sell instructions.

**Body bullets:**
- Multi-lens analytics with explicit non-gating layers
- Reproducible JSON artifacts and audit-friendly logs
- Enterprise API and dashboard are separate contracts

**Footer disclaimer (EN):**
> Draft observation only. Not investment advice. No guaranteed returns. Internal research tags: [HYPO] where applicable.

## Compression plugin IR (internal deck excerpt — do not mix with prophecy %)

- Zero weight-training domain packs (`zone_*.json`) — bench ~47.5% token saving on frozen 40-case panel, policy floor 0.47
- Not claimed: lossless translation, trading edge, or clinical outcomes
- SSOT: `compression_enterprise_executive_summary_v1.md` Plugin §

## Do not publish (checklist)

- Prophecy hit rates, shadow PnL, or "92%" style backfill stats
- Neuroscience proof or gut–brain ontology as science claims
- LG outcome guarantees

## Rail map

See `docs/final/artifacts/track_c_public_content_rail_map_v1_latest.md`
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8", newline="\n")
    meta = OUT.with_suffix(".meta.json")
    meta.write_text(
        json.dumps(
            {
                "schema": "track_c_public_content_template_v1",
                "generated_at_utc": ts,
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
