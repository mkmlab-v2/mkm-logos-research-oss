#!/usr/bin/env python3
"""Offline gate: logos-research Phase 2 hero embed (source markers + contract)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "projects/no1kmedi/src/app/logos-research/page.tsx"
EMBED = ROOT / "projects/no1kmedi/src/components/logos/LogosGraphStudioHeroEmbed.tsx"
LIB = ROOT / "projects/no1kmedi/src/lib/logosGraphStudioEmbed.ts"
COPY = ROOT / "projects/no1kmedi/marketing-site/logos-research-copy.json"
CONTRACT = ROOT / "docs/final/artifacts/logos_graph_studio_layer_b_ux_contract_v1.json"
OUT = ROOT / "reports/logos_research_home_embed_source_v1_latest.json"

SOURCE_MARKERS = (
    "LogosGraphStudioHeroEmbed",
    "data-layer-b-embed",
    "data-logos-graph-studio-embed",
    "data-embed-hero",
    "buildLogosGraphStudioEmbedUrl",
    "embed=hero",
    "autoplay",
    "hero_embed",
)


def main() -> int:
    errors: list[str] = []
    for path in (PAGE, EMBED, LIB, COPY, CONTRACT):
        if not path.is_file():
            errors.append(f"missing: {path}")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}))
        return 1

    blobs = (
        PAGE.read_text(encoding="utf-8")
        + EMBED.read_text(encoding="utf-8")
        + LIB.read_text(encoding="utf-8")
    )
    missing = [m for m in SOURCE_MARKERS if m not in blobs]
    if missing:
        errors.append(f"source markers missing: {missing}")

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") not in (
        "frozen_for_phase2_home_embed",
        "phase2_home_embed_live",
    ):
        errors.append(f"contract status unexpected: {contract.get('status')}")

    copy_doc = json.loads(COPY.read_text(encoding="utf-8"))
    if "hero_embed" not in copy_doc:
        errors.append("copy missing hero_embed")

    report = {
        "schema": "logos_research_home_embed_source_v1",
        "ok": len(errors) == 0,
        "source_markers_missing": missing,
        "errors": errors,
        "reproducible_command": "py scripts/check_logos_research_home_embed_source_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT), "errors": errors}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
