#!/usr/bin/env python3
"""Offline gate: mkmlife design kernel v1 wire (accent API + provider + public data)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKMLIFE = ROOT / "projects/mkm/mkm-life"
KERNEL_PUBLIC = MKMLIFE / "public/data/sasang_design_primitive_kernel_v1.json"
ORB_CSS_MAP = ROOT / "docs/final/artifacts/mkm_orb_design_kernel_css_map_v1_latest.json"
DEPTH_BOUNDARY = ROOT / "docs/final/artifacts/mkm_ask_one_ui_depth_boundary_v1_latest.json"
DEPTH_PUBLIC = MKMLIFE / "public/data/mkm_ask_one_ui_depth_boundary_v1.json"
DEPTH_PANEL = MKMLIFE / "components/magic-orb/ProductDepthContrastPanel.tsx"
COSMIC_LIB = MKMLIFE / "lib/mkmlifeCosmicAnchorV1.ts"
COSMIC_BRIDGE = MKMLIFE / "components/magic-orb/CosmicAnchorFrameBridge.tsx"
COSMIC_MANIFEST = MKMLIFE / "public/data/logos_cosmic_anchor_batch_v1_manifest_latest.json"
COSMIC_INDEX = MKMLIFE / "lib/mkmlifeCosmicAnchorBatchIndex.generated.ts"
LIB = MKMLIFE / "lib/mkmlifeDesignKernelV1.ts"
ORB_CSS_LIB = MKMLIFE / "lib/mkmlifeOrbKernelCssV1.ts"
API = MKMLIFE / "app/api/v1/design-kernel/accent/route.ts"
PROVIDER = MKMLIFE / "components/shell/MkmlifeDesignKernelProvider.tsx"
LAYOUT = MKMLIFE / "app/layout.tsx"


def main() -> int:
    missing = [
        p
        for p in (
            KERNEL_PUBLIC,
            ORB_CSS_MAP,
            DEPTH_BOUNDARY,
            DEPTH_PUBLIC,
            DEPTH_PANEL,
            COSMIC_LIB,
            COSMIC_BRIDGE,
            COSMIC_MANIFEST,
            COSMIC_INDEX,
            LIB,
            ORB_CSS_LIB,
            API,
            PROVIDER,
            LAYOUT,
        )
        if not p.is_file()
    ]
    if missing:
        for p in missing:
            print(f"MISSING: {p}", file=sys.stderr)
        return 1

    doc = json.loads(KERNEL_PUBLIC.read_text(encoding="utf-8"))
    pd = doc.get("product_depth", {}).get("mkmlife.com")
    if not pd or "myeongni" not in pd.get("extensions", []):
        print("mkmlife.com product_depth missing myeongni extension", file=sys.stderr)
        return 1

    layout = LAYOUT.read_text(encoding="utf-8")
    if "MkmlifeDesignKernelProvider" not in layout:
        print("layout missing MkmlifeDesignKernelProvider", file=sys.stderr)
        return 1

    provider = PROVIDER.read_text(encoding="utf-8")
    if "mkmlife-design-kernel-v1" not in provider:
        print("provider missing kernel marker", file=sys.stderr)
        return 1
    if "--orb-accent" not in provider:
        print("provider missing orb css var injection", file=sys.stderr)
        return 1

    api = API.read_text(encoding="utf-8")
    if "orb_accent_hex" not in api:
        print("accent API missing orb_accent_hex", file=sys.stderr)
        return 1

    depth = json.loads(DEPTH_BOUNDARY.read_text(encoding="utf-8"))
    if depth.get("schema") != "mkm_ask_one_ui_depth_boundary_v1":
        print("depth boundary schema mismatch", file=sys.stderr)
        return 1
    if depth.get("send_gate_default") != "HOLD":
        print("depth boundary send_gate must be HOLD", file=sys.stderr)
        return 1
    panel = DEPTH_PANEL.read_text(encoding="utf-8")
    if "ProductDepthContrastPanel" not in panel:
        print("depth panel missing", file=sys.stderr)
        return 1

    cosmic_manifest = json.loads(COSMIC_MANIFEST.read_text(encoding="utf-8"))
    if cosmic_manifest.get("schema") != "logos_cosmic_anchor_batch_v1_manifest":
        print("cosmic anchor manifest schema mismatch", file=sys.stderr)
        return 1
    if int(cosmic_manifest.get("anchor_count", 0)) < 30:
        print("cosmic anchor batch count must be >= 30", file=sys.stderr)
        return 1
    if not cosmic_manifest.get("forbidden_synthesis"):
        print("cosmic anchor manifest forbidden_synthesis must be true", file=sys.stderr)
        return 1
    cosmic_lib = COSMIC_LIB.read_text(encoding="utf-8")
    if "resolveCosmicAnchorForOrb" not in cosmic_lib:
        print("cosmic anchor lib missing resolver", file=sys.stderr)
        return 1
    if "mkmlifeCosmicAnchorBatchIndex.generated" not in cosmic_lib:
        print("cosmic anchor lib missing batch index import", file=sys.stderr)
        return 1
    if not COSMIC_INDEX.is_file():
        print("cosmic anchor batch index missing", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "overall_ok": True,
                "kernel_version": doc.get("kernel_version"),
                "depth_boundary_ok": True,
                "cosmic_anchor_batch_ok": True,
                "cosmic_anchor_count": cosmic_manifest.get("anchor_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
