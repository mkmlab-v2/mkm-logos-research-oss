#!/usr/bin/env python3
"""Verify air-gap Edge Encoder bundle integrity + local roundtrip [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "reports/edge_encoder_air_gap_bundle_v1_latest"
REPORT = ROOT / "reports/edge_encoder_air_gap_bundle_verify_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--entry-id", default="pilot_ninth_rib_55deg_v0")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_sdk_v1_lib import verify_air_gap_bundle

    errors, summary = verify_air_gap_bundle(
        workspace_root=ROOT,
        bundle_dir=args.bundle_dir,
        entry_id=args.entry_id,
    )
    doc = {"ok": not errors, "errors": errors, **summary}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
