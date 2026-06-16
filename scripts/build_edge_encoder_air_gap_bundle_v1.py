#!/usr/bin/env python3
"""Materialize offline Edge Encoder air-gap bundle [HYPO] B-track."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/edge_encoder_air_gap_bundle_v1_latest.json"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_sdk_v1_lib import materialize_air_gap_bundle

    summary = materialize_air_gap_bundle(workspace_root=ROOT)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
