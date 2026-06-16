#!/usr/bin/env python3
"""[HYPO] R1: rib55 L0 (pure geometry) vs L1 (sasang clamp) ablation — adjudication still required."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rib55_angle_overlay_v1_lib import (  # noqa: E402
    DEFAULT_MANIFEST,
    apply_sasang_l1_clamp,
    find_entry,
    load_manifest,
    render_entry_overlay,
    resolve_base_image,
    sha256_file,
)

DEFAULT_SASANG = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
OUT_ART = ROOT / "docs/final/artifacts/rib55_l0_l1_ablation_v1_latest.json"
OUT_REPORT = ROOT / "reports/rib55_l0_l1_ablation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--entry-id", default=None)
    ap.add_argument("--sasang", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs/final/artifacts")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    entry = find_entry(manifest, args.entry_id)
    eid = str(entry.get("entry_id", "pilot"))
    base_path = resolve_base_image(entry, workspace_root=ROOT, fetch=False)

    if not args.sasang.is_file():
        raise SystemExit(f"missing sasang lens: {args.sasang}")
    sasang_doc = json.loads(args.sasang.read_text(encoding="utf-8"))

    layers = entry.get("overlays") or []
    if not layers:
        raise SystemExit("manifest entry has no overlays")

    l0_layer = copy.deepcopy(layers[0])
    l1_layer = apply_sasang_l1_clamp(copy.deepcopy(layers[0]), sasang_doc)

    l0_png = args.out_dir / f"rib55_ablation_l0_{eid}_latest.png"
    l1_png = args.out_dir / f"rib55_ablation_l1_{eid}_latest.png"

    l0_entry = {**entry, "overlays": [l0_layer]}
    l1_entry = {**entry, "overlays": [l1_layer]}

    r0 = render_entry_overlay(l0_entry, base_path, l0_png)
    r1 = render_entry_overlay(l1_entry, base_path, l1_png)

    angle_l0 = float(l0_layer.get("angle_deg") or 0)
    angle_l1 = float(l1_layer.get("angle_deg") or 0)

    doc = {
        "schema": "rib55_l0_l1_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "adjudication_required": True,
        "entry_id": eid,
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "sasang_lens": str(args.sasang.relative_to(ROOT)).replace("\\", "/"),
        "l0": {
            "mode": "L0_geometry_only",
            "angle_deg": angle_l0,
            "output": str(l0_png.relative_to(ROOT)).replace("\\", "/"),
            "sha256": r0.get("output_sha256"),
        },
        "l1": {
            "mode": "L1_sasang_clamp",
            "angle_deg": angle_l1,
            "angle_delta": round(angle_l1 - angle_l0, 4),
            "output": str(l1_png.relative_to(ROOT)).replace("\\", "/"),
            "sha256": r1.get("output_sha256"),
        },
        "pixels_differ": r0.get("output_sha256") != r1.get("output_sha256"),
        "policy": "Charter R1 — not verification complete; human adjudication still required",
        "ok": True,
    }

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT_ART), "angle_delta": doc["l1"]["angle_delta"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
