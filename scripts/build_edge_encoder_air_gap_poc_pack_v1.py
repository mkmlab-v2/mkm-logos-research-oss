#!/usr/bin/env python3
"""Build air-gap Edge Encoder PoC pack artifact [HYPO] B-track."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/edge_encoder_air_gap_poc_pack_v1_latest.json"
REPORT = ROOT / "reports/edge_encoder_air_gap_poc_pack_v1_latest.json"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_sdk_v1_lib import build_air_gap_poc_pack

    doc = build_air_gap_poc_pack(workspace_root=ROOT)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "mode": doc["deployment_mode"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
