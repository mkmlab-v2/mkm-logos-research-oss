#!/usr/bin/env python3
"""Smoke gate: coord wire schema + bilateral SHA256 determinism. [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/edge_encoder_coord_wire_determinism_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from scripts.edge_encoder_spec_v1_lib import (
        check_coord_wire_determinism,
        load_coord_wire_from_example,
        validate_coord_wire_minimal,
    )

    wire = load_coord_wire_from_example()
    errors = validate_coord_wire_minimal(wire) + check_coord_wire_determinism(wire, workspace_root=ROOT)

    doc = {
        "schema": "edge_encoder_coord_wire_determinism_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": len(errors) == 0,
        "errors": errors,
        "wire_entry_id": (wire.get("coord_inject") or {}).get("entry_id"),
        "base_sha256_prefix": str(wire.get("base_sha256") or "")[:16],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "errors": errors, "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
