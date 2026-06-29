#!/usr/bin/env python3
"""Gate: showroom subgraph audit slice present + NON_GATING contract ([HYPO])."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_subgraph_audit_slice_v1.json"
)
DEFAULT_OUT = ROOT / "reports/showroom_logos_subgraph_audit_slice_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check(*, slice_path: Path, min_paths: int) -> dict[str, Any]:
    if not slice_path.is_file():
        return {
            "schema": "showroom_logos_subgraph_audit_slice_gate_v1",
            "generated_at_utc": _utc(),
            "gate_pass": False,
            "gate_failures": ["slice_missing"],
        }
    doc = json.loads(slice_path.read_text(encoding="utf-8-sig"))
    failures: list[str] = []
    if doc.get("schema_version") != "showroom_logos_subgraph_audit_slice_v1":
        failures.append("schema_version mismatch")
    if doc.get("send_gate") != "HOLD":
        failures.append("send_gate must be HOLD")
    if doc.get("non_gating") is not True:
        failures.append("non_gating must be true")
    disc = doc.get("disclaimer") or {}
    if disc.get("gating_status") != "NON_GATING":
        failures.append("disclaimer.gating_status must be NON_GATING")
    rs = doc.get("router_snapshot") or {}
    path_count = int(rs.get("path_count") or 0)
    if path_count < min_paths:
        failures.append(f"path_count {path_count} < min_paths {min_paths}")
    if len(doc.get("paths_public") or []) < min_paths:
        failures.append("paths_public too short")
    if len(doc.get("audit_rows") or []) < 4:
        failures.append("audit_rows too short")

    return {
        "schema": "showroom_logos_subgraph_audit_slice_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "slice_path": str(slice_path.relative_to(ROOT)).replace("\\", "/")
        if slice_path.is_relative_to(ROOT)
        else str(slice_path),
        "path_count": path_count,
        "gate_pass": len(failures) == 0,
        "gate_failures": failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-paths", type=int, default=1)
    args = ap.parse_args()

    doc = check(slice_path=args.slice_json, min_paths=args.min_paths)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_pass"], "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
