# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.5}
# Balance: 93
# Purpose: Validate unified state snapshot contract and reject null drift.
# Keywords: validate, unified, schema, contract, null
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "docs/final/artifacts/unified_state_snapshot_v1_latest.json"

REQUIRED_TOP = ["schema", "schema_version", "generated_at_utc", "state_nodes", "summary"]
REQUIRED_NODE_FIELDS = ["status", "stage", "readiness", "reasons", "source_generated_at_utc", "meta"]
REQUIRED_SUMMARY_FIELDS = ["status", "stage", "readiness", "reasons"]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_none_like(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP:
        if key not in payload:
            errors.append(f"missing_top:{key}")

    nodes = payload.get("state_nodes")
    if not isinstance(nodes, dict):
        errors.append("invalid:state_nodes_not_object")
        return errors

    for node_name, node_val in nodes.items():
        if not isinstance(node_val, dict):
            errors.append(f"invalid:node_not_object:{node_name}")
            continue
        for f in REQUIRED_NODE_FIELDS:
            if f not in node_val:
                errors.append(f"missing_node_field:{node_name}:{f}")
            elif f != "source_generated_at_utc" and _is_none_like(node_val.get(f)):
                errors.append(f"none_like_node_field:{node_name}:{f}")
        if not isinstance(node_val.get("reasons"), list):
            errors.append(f"invalid_node_reasons_not_list:{node_name}")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("invalid:summary_not_object")
    else:
        for f in REQUIRED_SUMMARY_FIELDS:
            if f not in summary:
                errors.append(f"missing_summary_field:{f}")
            elif f != "reasons" and _is_none_like(summary.get(f)):
                errors.append(f"none_like_summary_field:{f}")
        if not isinstance(summary.get("reasons"), list):
            errors.append("invalid_summary_reasons_not_list")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate unified_state_snapshot_v1 artifact.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    args = ap.parse_args()
    src = args.input if args.input.is_absolute() else ROOT / args.input
    payload = _load(src)
    errors = validate(payload)
    if errors:
        print("VALIDATION_FAIL")
        for e in errors:
            print(e)
        return 1
    print("VALIDATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
