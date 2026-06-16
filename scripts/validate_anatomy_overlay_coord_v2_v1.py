#!/usr/bin/env python3
"""[HYPO] Validate rib55 manifest anatomy_overlay_coord_v2 extension."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
OUT = ROOT / "docs/final/artifacts/anatomy_overlay_coord_v2_validation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    if not args.manifest.is_file():
        raise SystemExit(f"missing manifest: {args.manifest}")

    doc = json.loads(args.manifest.read_text(encoding="utf-8"))
    coord = doc.get("coord_v2") or {}
    checks = [
        {"name": "coord_spec_v2", "ok": doc.get("coord_spec_v2") == "anatomy_overlay_coord_v2"},
        {"name": "coord_v2_schema_pointer", "ok": bool(doc.get("coord_v2_schema_pointer"))},
        {"name": "clamp_policy", "ok": bool(coord.get("clamp_policy"))},
        {"name": "r1_ablation_link", "ok": bool(coord.get("r1_ablation", {}).get("artifact"))},
        {"name": "layer_modes", "ok": bool(coord.get("layer_modes"))},
        {
            "name": "send_gate_hold",
            "ok": doc.get("send_gate") == "HOLD" and coord.get("ready_for_external_send") is False,
        },
    ]

    report = {
        "schema": "anatomy_overlay_coord_v2_validation_v1",
        "generated_at_utc": _utc(),
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "checks": checks,
        "ok": all(c["ok"] for c in checks),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
