#!/usr/bin/env python3
"""Check RS channel policy readiness gate from locked artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "docs" / "final" / "artifacts" / "mkm_l1_rs_channel_policy_v1.json"
COMPARE = ROOT / "docs" / "final" / "artifacts" / "mkm_l1_rs_stub_compare_latest.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_l1_rs_policy_gate_latest.json"
DEVICE_PROFILES = ROOT / "docs" / "final" / "artifacts" / "dynamic_stress_causality_device_profiles_v1.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=POLICY)
    ap.add_argument("--compare", type=Path, default=COMPARE)
    ap.add_argument("--device-profiles", type=Path, default=DEVICE_PROFILES)
    ap.add_argument("--device-profile", type=str, default="generic_lab")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--max-block-ratio", type=float, default=0.6)
    args = ap.parse_args()

    p = _load(args.policy)
    c = _load(args.compare)
    d = _load(args.device_profiles)

    allow = int(p.get("policy", {}).get("allow_rule_count") or 0)
    block = int(p.get("policy", {}).get("block_rule_count") or 0)
    total = max(1, allow + block)
    block_ratio = block / total

    status = "GO_RESEARCH_LOCKED"
    reasons: list[str] = []
    if p.get("schema") != "mkm_l1_rs_channel_policy_v1":
        status = "HOLD_SCHEMA_MISMATCH"
        reasons.append("policy_schema_invalid")
    if c.get("decision_hint", {}).get("status") != "CHANNEL_AWARE_RS_POLICY_LOCKED":
        status = "HOLD_COMPARE_NOT_LOCKED"
        reasons.append("compare_status_not_locked")
    if block_ratio > float(args.max_block_ratio):
        status = "HOLD_BLOCK_RATIO_HIGH"
        reasons.append("block_ratio_above_threshold")
    profiles = d.get("profiles", [])
    profile_map = {}
    if isinstance(profiles, list):
        for row in profiles:
            if isinstance(row, dict) and isinstance(row.get("profile_id"), str):
                profile_map[row["profile_id"]] = row
    selected = profile_map.get(args.device_profile)
    if selected is None:
        status = "HOLD_DEVICE_PROFILE_MISSING"
        reasons.append("device_profile_not_found")

    doc = {
        "schema": "mkm_l1_rs_policy_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "research_only",
        "inputs": {
            "policy": str(args.policy).replace("\\", "/"),
            "compare": str(args.compare).replace("\\", "/"),
            "device_profiles": str(args.device_profiles).replace("\\", "/"),
            "device_profile": args.device_profile,
            "max_block_ratio": float(args.max_block_ratio),
        },
        "metrics": {
            "allow_rule_count": allow,
            "block_rule_count": block,
            "block_ratio": block_ratio,
        },
        "status": status,
        "reasons": reasons,
        "selected_device_profile": selected,
        "note": "Research gate only. No production promotion implied.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), "status": status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
