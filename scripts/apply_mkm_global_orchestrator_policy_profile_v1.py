#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "mkm_global_orchestrator_policy_v1.json"

PROFILES: dict[str, dict[str, float]] = {
    "research": {
        "go_confidence_cut": 0.70,
        "go_direction_abs_cut": 0.25,
        "hold_confidence_cut": 0.35,
        "hold_direction_abs_cut": 0.10,
    },
    "prod_conditional_go": {
        "go_confidence_cut": 0.53,
        "go_direction_abs_cut": 0.14,
        "hold_confidence_cut": 0.35,
        "hold_direction_abs_cut": 0.10,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply orchestrator decision-policy profile.")
    ap.add_argument("--profile", choices=sorted(PROFILES.keys()), required=True)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_POLICY)
    args = ap.parse_args()

    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    doc = _read_json(policy_path)
    decision_policy = doc.get("decision_policy") if isinstance(doc.get("decision_policy"), dict) else {}
    profile_values = PROFILES[args.profile]
    decision_policy.update(profile_values)
    decision_policy.setdefault("fail_closed_action", "HOLD")
    doc["decision_policy"] = decision_policy
    doc["active_profile"] = args.profile
    doc["profile_applied_at_utc"] = _now()
    doc["available_profiles"] = sorted(PROFILES.keys())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "profile": args.profile,
                "out": str(out_path),
                "decision_policy": decision_policy,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
