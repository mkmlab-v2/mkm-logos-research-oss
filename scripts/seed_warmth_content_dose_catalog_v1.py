#!/usr/bin/env python3
"""Seed WTT content dose catalog (B-track pilot corpus · [HYPO])."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_v1.json"

SEEDS = [
    ("poem", "warm", 0.35, 0.82, 0.5, 0.3, True, ["low_pressure_only"]),
    ("poem", "warm", 0.55, 0.7, 0.65, 0.45, True, ["low_pressure_only"]),
    ("poem", "cool", 0.6, 0.45, 0.4, 0.55, False, []),
    ("poem", "warm", 0.75, 0.55, 0.8, 0.7, True, ["trauma_heavy"]),
    ("short_story", "warm", 0.45, 0.75, 0.6, 0.4, True, ["low_pressure_only"]),
    ("short_story", "warm", 0.5, 0.8, 0.55, 0.42, True, []),
    ("short_story", "direct", 0.65, 0.5, 0.5, 0.6, True, []),
    ("short_story", "cool", 0.7, 0.4, 0.45, 0.65, False, ["avoid_long_text"]),
    ("novel_excerpt", "warm", 0.48, 0.72, 0.58, 0.38, True, []),
    ("novel_excerpt", "mixed", 0.68, 0.55, 0.72, 0.62, True, []),
    ("webtoon_episode", "warm", 0.52, 0.78, 0.62, 0.44, True, []),
    ("webtoon_episode", "warm", 0.58, 0.68, 0.7, 0.5, True, []),
    ("webtoon_episode", "cool", 0.72, 0.42, 0.55, 0.68, False, []),
    ("music_track", "warm", 0.3, 0.85, 0.35, 0.2, True, []),
    ("music_track", "warm", 0.4, 0.75, 0.45, 0.28, True, []),
    ("music_track", "direct", 0.55, 0.6, 0.5, 0.48, True, []),
    ("essay", "warm", 0.38, 0.8, 0.48, 0.32, True, ["low_pressure_only"]),
    ("essay", "direct", 0.5, 0.65, 0.52, 0.4, True, []),
    ("essay", "warm", 0.62, 0.58, 0.68, 0.55, True, []),
    ("essay", "cool", 0.78, 0.35, 0.6, 0.75, False, ["guilt_spiral"]),
    ("script_other", "warm", 0.42, 0.77, 0.54, 0.36, True, []),
    ("script_other", "warm", 0.47, 0.73, 0.57, 0.41, True, []),
    ("script_other", "mixed", 0.66, 0.52, 0.64, 0.58, True, []),
    ("script_other", "cool", 0.8, 0.3, 0.7, 0.8, False, ["trauma_heavy"]),
]


def main() -> int:
    items = []
    for i, (medium, style, intensity, warmth, cath, beta, recovery, risks) in enumerate(SEEDS, start=1):
        cid = f"wtt_catalog_{medium}_{i:02d}"
        items.append(
            {
                "schema": "warmth_content_dose_v1",
                "version": "1.0.0",
                "dose_version": f"2026-06-11.catalog.{cid}",
                "hypothesis_class": "HYPO",
                "track": "B",
                "research_only": True,
                "content_id": cid,
                "medium": medium,
                "title_ko": f"WTT 파일럿 {medium} #{i}",
                "dose": {
                    "intensity_0_1": intensity,
                    "warmth_0_1": warmth,
                    "catharsis_0_1": cath,
                    "narrative_tension_beta_0_1": beta,
                    "recovery_arc_present": recovery,
                    "delivery_style": style,
                    "risk_tags": risks,
                },
                "provenance": {
                    "source": "batch_generate",
                    "experiment_id": "wtt_epb_pilot_01_catalog",
                    "slug": "wtt-epb-pilot-01",
                },
            }
        )

    catalog = {
        "schema": "warmth_content_dose_catalog_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "item_count": len(items),
        "items": items,
        "provenance": {
            "source": "seed_warmth_content_dose_catalog_v1",
            "experiment_id": "wtt_epb_pilot_01",
            "slug": "wtt-epb-pilot-01",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "item_count": len(items), "out": str(OUT.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
