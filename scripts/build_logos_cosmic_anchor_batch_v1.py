#!/usr/bin/env python3
"""Batch-build Logos cosmic anchors from motif registry (Top 100 pipeline).

Reproducible chain:
  py scripts/build_logos_motif_registry_top100_v1.py
  py scripts/build_logos_cosmic_anchor_batch_v1.py
  py scripts/build_logos_anchor_resonance_stats_v1.py

Uses gematria_bridge_v1 (S,L,K,M) SSOT; thermo alias derived only.
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

from scripts.core.logos_cosmic_anchor_build_v1 import build_anchor_row, public_row

REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
OUT_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"

PRESET_LOOKUP: dict[str, str] = {
    "job_suffering_reason": "cosmic_anchor_seed_jhn_12_24",
    "motif_light": "cosmic_anchor_light_jhn_1_5",
    "motif_door": "cosmic_anchor_door_jhn_10_9",
    "motif_star": "cosmic_anchor_star_rev_22_16",
}

MKMLIFE_ROOT = ROOT / "projects/mkm/mkm-life"
MKMLIFE_BATCH_PUBLIC = MKMLIFE_ROOT / "public/data/logos_cosmic_anchor_batch_v1"
MKMLIFE_BATCH_MANIFEST = MKMLIFE_ROOT / "public/data/logos_cosmic_anchor_batch_v1_manifest_latest.json"
MKMLIFE_BATCH_INDEX = MKMLIFE_ROOT / "lib/mkmlifeCosmicAnchorBatchIndex.generated.ts"


def _load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_batch(
    *,
    registry_path: Path = REGISTRY,
    out_dir: Path = OUT_DIR,
    compute_thermo_alias: bool = True,
    spread_aware_ranking: bool = True,
) -> dict[str, Any]:
    registry = _load_registry(registry_path)
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)

    enabled = [e for e in registry.get("entries", []) if e.get("enabled")]
    anchor_rows: list[dict[str, Any]] = []
    paths: dict[str, str] = {}
    lookup_by_verse: dict[str, str] = {}
    skipped: list[str] = []

    for entry in enabled:
        anchor_id = entry.get("anchor_id")
        file_stem = entry.get("file_stem")
        if not anchor_id or not file_stem:
            skipped.append(str(entry.get("slot_id")))
            continue
        row = build_anchor_row(
            entry,
            generated_at_utc=generated_at_utc,
            compute_thermo_alias=compute_thermo_alias,
            spread_aware_ranking=spread_aware_ranking,
        )
        public = public_row(row)
        out_path = out_dir / f"{file_stem}.json"
        out_path.write_text(
            json.dumps(public, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        anchor_rows.append(public)
        paths[file_stem] = out_path.relative_to(ROOT).as_posix()
        for ref in entry.get("verse_refs") or []:
            lookup_by_verse[ref] = anchor_id

    active_stems = set(paths.keys())
    for stale in out_dir.glob("*.json"):
        if stale.stem not in active_stems:
            stale.unlink()

    manifest = {
        "schema": "logos_cosmic_anchor_batch_v1_manifest",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "registry_path": registry_path.relative_to(ROOT).as_posix(),
        "registry_slot_count": int(registry.get("slot_count", 0)),
        "registry_enabled_count": len(enabled),
        "anchor_count": len(anchor_rows),
        "skipped_slot_ids": skipped,
        "anchor_ids": [r["anchor_id"] for r in anchor_rows],
        "paths": paths,
        "lookup_by_verse_ref": lookup_by_verse,
        "lookup_by_preset_id": dict(PRESET_LOOKUP),
        "kernel_recipe_id": "gematria_bridge_v1",
        "thermo_alias_recipe_id": "gematria_thermo_alias_v1",
        "spread_aware_ranking": spread_aware_ranking,
        "reproducible_command": "py scripts/build_logos_cosmic_anchor_batch_v1.py",
        "formalization_schema": "docs/final/schemas/logos_cosmic_anchor_formalization_v1.schema.json",
        "resonance_stats_path": "docs/final/artifacts/logos_anchor_resonance_stats_latest.json",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _sync_mkmlife_batch(manifest, out_dir)
    return manifest


def _safe_ts_ident(stem: str) -> str:
    ident = stem.replace("-", "_")
    if ident[0].isdigit():
        return f"anchor_{ident}"
    return ident


def _write_mkmlife_batch_index(stems: list[str]) -> None:
    lines = [
        "/** AUTO-GENERATED — py scripts/build_logos_cosmic_anchor_batch_v1.py */",
        "/* eslint-disable */",
    ]
    idents: list[tuple[str, str]] = []
    for stem in sorted(stems):
        ident = _safe_ts_ident(stem)
        lines.append(
            f"import {ident}Doc from '../public/data/logos_cosmic_anchor_batch_v1/{stem}.json'"
        )
        idents.append((ident, stem))
    lines.append("")
    lines.append("export const BATCH_ANCHOR_BY_ID: Record<string, any> = {")
    for ident, _stem in idents:
        lines.append(f"  [{ident}Doc.anchor_id]: {ident}Doc,")
    lines.append("}")
    lines.append("")
    MKMLIFE_BATCH_INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sync_mkmlife_batch(manifest: dict[str, Any], out_dir: Path) -> None:
    MKMLIFE_BATCH_PUBLIC.mkdir(parents=True, exist_ok=True)
    stems = sorted(manifest.get("paths", {}).keys())
    for stem in stems:
        src = out_dir / f"{stem}.json"
        dst = MKMLIFE_BATCH_PUBLIC / f"{stem}.json"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    public_manifest = {
        **manifest,
        "mkmlife_public_dir": "public/data/logos_cosmic_anchor_batch_v1",
        "lookup_manifest_fn": "lookup_cosmic_anchor_by_verse_ref_v1",
    }
    MKMLIFE_BATCH_MANIFEST.write_text(
        json.dumps(public_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_mkmlife_batch_index(stems)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY,
        help="motif registry JSON path",
    )
    parser.add_argument(
        "--no-thermo-alias",
        action="store_true",
        help="skip derived Ei/Pf/Dd/Hc recompute (use registry legacy only)",
    )
    parser.add_argument(
        "--no-spread-aware-ranking",
        action="store_true",
        help="use plain cosine ranking (batch research default: spread-aware)",
    )
    args = parser.parse_args()
    manifest = build_batch(
        registry_path=args.registry,
        compute_thermo_alias=not args.no_thermo_alias,
        spread_aware_ranking=not args.no_spread_aware_ranking,
    )
    print(f"WROTE: {OUT_DIR} ({manifest['anchor_count']} anchors)")
    print(f"WROTE: {MANIFEST}")
    print(f"SYNC: {MKMLIFE_BATCH_PUBLIC} ({len(manifest.get('paths', {}))} files)")
    print(f"SYNC: {MKMLIFE_BATCH_MANIFEST}")
    print(f"SYNC: {MKMLIFE_BATCH_INDEX}")
    if manifest.get("skipped_slot_ids"):
        print(f"SKIPPED: {manifest['skipped_slot_ids']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
