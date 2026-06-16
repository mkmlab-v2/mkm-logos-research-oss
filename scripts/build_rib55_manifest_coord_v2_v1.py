#!/usr/bin/env python3
"""[HYPO] R2: attach anatomy_overlay_coord_v2 block to rib55 manifest from R1 ablation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
ABLATION = ROOT / "docs/final/artifacts/rib55_l0_l1_ablation_v1_latest.json"
SCHEMA = ROOT / "docs/final/artifacts/anatomy_overlay_coord_v2_schema_v1.json"
OUT_REPORT = ROOT / "reports/rib55_manifest_coord_v2_build_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--ablation", type=Path, default=ABLATION)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for path in (args.manifest, args.ablation, SCHEMA):
        if not path.is_file():
            raise SystemExit(f"missing: {path}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ablation = json.loads(args.ablation.read_text(encoding="utf-8"))
    if not ablation.get("ok"):
        raise SystemExit(f"ablation not ok: {args.ablation}")

    entry_id = str(ablation.get("entry_id", ""))
    layer_ids = []
    for entry in manifest.get("entries") or []:
        if entry.get("entry_id") == entry_id:
            layer_ids = [str(x.get("layer_id")) for x in entry.get("overlays") or [] if x.get("layer_id")]

    coord_v2 = {
        "schema": "anatomy_overlay_coord_v2",
        "generated_at_utc": _utc(),
        "clamp_policy": {
            "lane": "L1_sasang_clamp",
            "angle_bounds_deg": [40.0, 70.0],
            "point_nudge_max": 0.04,
            "sasang_lens_pointer": ablation.get("sasang_lens"),
            "function": "scripts.rib55_angle_overlay_v1_lib.apply_sasang_l1_clamp",
        },
        "r1_ablation": {
            "artifact": str(args.ablation.relative_to(ROOT)).replace("\\", "/"),
            "entry_id": entry_id,
            "angle_delta": ablation.get("l1", {}).get("angle_delta"),
            "pixels_differ": ablation.get("pixels_differ"),
            "l0_output": ablation.get("l0", {}).get("output"),
            "l1_output": ablation.get("l1", {}).get("output"),
        },
        "layer_modes": {
            lid: {
                "L0_geometry_only": {"angle_deg": ablation.get("l0", {}).get("angle_deg")},
                "L1_sasang_clamp": {"angle_deg": ablation.get("l1", {}).get("angle_deg")},
            }
            for lid in layer_ids
        },
        "adjudication_required": True,
        "ready_for_external_send": False,
    }

    manifest["coord_spec_v2"] = "anatomy_overlay_coord_v2"
    manifest["coord_v2_schema_pointer"] = str(SCHEMA.relative_to(ROOT)).replace("\\", "/")
    manifest["coord_v2"] = coord_v2

    report = {
        "schema": "rib55_manifest_coord_v2_build_v1",
        "generated_at_utc": _utc(),
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "entry_id": entry_id,
        "layer_count": len(layer_ids),
        "coord_spec_v2": manifest["coord_spec_v2"],
        "ok": True,
    }

    if not args.dry_run:
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
