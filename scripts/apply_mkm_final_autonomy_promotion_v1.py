#!/usr/bin/env python3
"""Apply MKM final autonomy promotion by updating staged inclusion policy guardrails."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "mkm_final_autonomy_gate_v1_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "three_lens_staged_inclusion_policy_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_final_autonomy_promotion_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true", help="Apply even if gate decision is HOLD_SAFE_MODE.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gate_path = args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    gate = _read_json(gate_path)
    policy = _read_json(policy_path)
    decision = str(gate.get("decision") or "HOLD_SAFE_MODE")
    can_apply = decision == "PROMOTE_FINAL_AUTONOMY" or args.force

    promoted = False
    direct_bridge_status_before = None
    direct_bridge_status_after = None
    rows = policy.get("features") if isinstance(policy.get("features"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("id") or "") == "direct_live_trigger_bridge":
            direct_bridge_status_before = str(row.get("status") or "")
            if can_apply:
                row["status"] = "enabled"
            direct_bridge_status_after = str(row.get("status") or "")
            promoted = promoted or (direct_bridge_status_before != direct_bridge_status_after)

    guardrails = policy.get("guardrails") if isinstance(policy.get("guardrails"), dict) else {}
    if can_apply:
        guardrails["research_only"] = False
        guardrails["human_signoff_required"] = False
        guardrails["auto_bridge_to_live_forbidden"] = False
    policy["guardrails"] = guardrails
    policy["mode"] = "final_autonomy" if can_apply else policy.get("mode", "staged_rollout")
    policy["generated_at_utc"] = _now()

    if can_apply and not args.dry_run:
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload: dict[str, Any] = {
        "schema": "mkm_final_autonomy_promotion_v1",
        "generated_at_utc": _now(),
        "gate_json": str(gate_path),
        "policy_json": str(policy_path),
        "gate_decision": decision,
        "force": bool(args.force),
        "dry_run": bool(args.dry_run),
        "applied": bool(can_apply and not args.dry_run),
        "promoted": bool(promoted and can_apply),
        "direct_live_trigger_bridge_status_before": direct_bridge_status_before,
        "direct_live_trigger_bridge_status_after": direct_bridge_status_after,
        "guardrails_after": guardrails,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "applied": payload["applied"], "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
