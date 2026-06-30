#!/usr/bin/env python3
"""Check JEMA OS coordinate envelope v1 artifact + A2A/bounded-lane cross-refs."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/jema_os_coordinate_envelope_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/jema_os_coordinate_envelope_v1.schema.json"
REPORT = ROOT / "reports/jema_os_coordinate_envelope_v1_check_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_envelope(doc: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    issues: list[str] = []
    a2a = doc.get("a2a_peer") if isinstance(doc.get("a2a_peer"), dict) else {}
    peer = a2a.get("peer_handoff_pointer")
    peer_ok = bool(peer) and (root / str(peer)).is_file()
    if not peer_ok:
        issues.append("a2a_peer_handoff_missing")
    bounded_ref = a2a.get("bounded_lane_loop_ref")
    bounded_ok = bool(bounded_ref) and (root / str(bounded_ref)).is_file()
    if not bounded_ok:
        issues.append("bounded_lane_loop_ref_missing")
    if doc.get("send_gate") != "HOLD":
        issues.append("send_gate_not_hold")
    guard = doc.get("fail_comp_004_guard") if isinstance(doc.get("fail_comp_004_guard"), dict) else {}
    if guard.get("compression_kpi_weight_in_inference") != 0:
        issues.append("fail_comp_004_weight_nonzero")
    if guard.get("lens_score_headline_merge") is not False:
        issues.append("fail_comp_004_merge_not_false")
    depth = str(doc.get("read_depth") or "")
    umr = doc.get("umr_binding") if isinstance(doc.get("umr_binding"), dict) else {}
    tier = str(umr.get("resolution_tier") or "")
    if depth == "skim" and tier != "low_res":
        issues.append("skim_tier_mismatch")
    if depth == "deep" and tier != "high_res":
        issues.append("deep_tier_mismatch")
    return {
        "ok": not issues,
        "issues": issues,
        "a2a_peer_ok": peer_ok,
        "bounded_lane_loop_ok": bounded_ok,
        "read_depth": depth,
        "resolution_tier": tier,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--report", type=Path, default=REPORT)
    args = ap.parse_args()
    if not args.artifact.is_file():
        print(f"missing artifact: {args.artifact}", file=sys.stderr)
        return 1
    doc = json.loads(args.artifact.read_text(encoding="utf-8"))
    result = check_envelope(doc)
    report = {
        "schema": "jema_os_coordinate_envelope_v1_check",
        "generated_at_utc": _utc(),
        "artifact": str(args.artifact.relative_to(ROOT)).replace("\\", "/"),
        "schema_ref": str(SCHEMA.relative_to(ROOT)).replace("\\", "/"),
        **result,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
