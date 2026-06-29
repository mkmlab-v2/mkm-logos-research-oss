#!/usr/bin/env python3
"""Batch-build Logos cosmic anchors — B-track sandbox bridge (research spread).

Reproducible:
  py scripts/build_logos_cosmic_anchor_batch_sandbox_v1.py

Uses gematria_bridge_sandbox_v1 for vector_4d; production SSOT unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.gematria_to_4d_bridge_sandbox_v1 import RECIPE_ID
from scripts.core.logos_cosmic_anchor_build_v1 import build_anchor_row, public_row

REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_sandbox_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_sandbox_v1_manifest_latest.json"


def build_sandbox_batch(
    *,
    registry_path: Path = REGISTRY,
    out_dir: Path = OUT_DIR,
) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)

    enabled = [e for e in registry.get("entries", []) if e.get("enabled")]
    paths: dict[str, str] = {}
    anchor_ids: list[str] = []

    for entry in enabled:
        anchor_id = entry.get("anchor_id")
        file_stem = entry.get("file_stem")
        if not anchor_id or not file_stem:
            continue
        row = build_anchor_row(
            entry,
            generated_at_utc=generated_at_utc,
            compute_thermo_alias=True,
            spread_aware_ranking=True,
            use_sandbox_bridge=True,
        )
        public = public_row(row)
        out_path = out_dir / f"{file_stem}.json"
        out_path.write_text(
            json.dumps(public, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        paths[file_stem] = out_path.relative_to(ROOT).as_posix()
        anchor_ids.append(anchor_id)

    manifest = {
        "schema": "logos_cosmic_anchor_batch_sandbox_v1_manifest",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "production_kernel_recipe_id": "gematria_bridge_v1",
        "sandbox_kernel_recipe_id": RECIPE_ID,
        "registry_path": registry_path.relative_to(ROOT).as_posix(),
        "anchor_count": len(anchor_ids),
        "anchor_ids": anchor_ids,
        "paths": paths,
        "spread_aware_ranking": True,
        "reproducible_command": "py scripts/build_logos_cosmic_anchor_batch_sandbox_v1.py",
        "resonance_stats_path": "docs/final/artifacts/logos_anchor_resonance_stats_sandbox_latest.json",
        "dual_gate_report_path": "docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()
    manifest = build_sandbox_batch(registry_path=args.registry)
    print(f"WROTE: {OUT_DIR} ({manifest['anchor_count']} sandbox anchors)")
    print(f"WROTE: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
