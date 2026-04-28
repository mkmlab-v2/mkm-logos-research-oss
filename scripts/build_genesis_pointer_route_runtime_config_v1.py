#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
IN_DEFAULT = ART / "genesis_pointer_routing_decision_latest.json"
OUT_DEFAULT = ART / "genesis_pointer_route_runtime_config_latest.json"
FOLDER_POLICY_DEFAULT = ART / "pointerguard_folder_policy_latest.json"
APPLY_PROMOTION_DEFAULT = ART / "pointerguard_apply_go_promotion_decision_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-json", type=Path, default=IN_DEFAULT)
    ap.add_argument("--folder-policy-json", type=Path, default=FOLDER_POLICY_DEFAULT)
    ap.add_argument("--apply-promotion-json", type=Path, default=APPLY_PROMOTION_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    decision_path = args.decision_json if args.decision_json.is_absolute() else ROOT / args.decision_json
    folder_policy_path = (
        args.folder_policy_json if args.folder_policy_json.is_absolute() else ROOT / args.folder_policy_json
    )
    apply_promotion_path = (
        args.apply_promotion_json if args.apply_promotion_json.is_absolute() else ROOT / args.apply_promotion_json
    )
    dec = _read_json(decision_path)
    folder_policy = _read_json(folder_policy_path)
    apply_promotion = _read_json(apply_promotion_path)
    decision = str(dec.get("decision", "HOLD_POINTER_ROUTE"))
    route_mode = str(dec.get("route_mode", "track_a_primary"))
    apply_go_enabled = bool(apply_promotion.get("promote_apply_path_to_go", False))
    if decision == "ENABLE_POINTER_ROUTE" and not apply_go_enabled:
        decision = "SHADOW_POINTER_ROUTE"
        route_mode = "pointer_shadow"
    stats = dec.get("stats", {})

    pointer_enabled = decision == "ENABLE_POINTER_ROUTE"
    pointer_shadow = decision == "SHADOW_POINTER_ROUTE"

    config = {
        "schema": "genesis_pointer_route_runtime_config_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "decision_json": str(decision_path),
            "folder_policy_json": str(folder_policy_path),
            "apply_promotion_json": str(apply_promotion_path),
        },
        "routing": {
            "decision": decision,
            "route_mode": route_mode,
            "pointer_enabled": pointer_enabled,
            "pointer_shadow": pointer_shadow,
            "track_a_primary": route_mode == "track_a_primary",
            "disable_switch_env": "GENESIS_POINTER_ROUTE_FORCE_DISABLE",
        },
        "folder_policy": {
            "schema": str(folder_policy.get("schema", "unknown")),
            "policy_default": str(folder_policy.get("policy_default", "deny_unless_allowlisted")),
            "rows": [
                {
                    "path_pattern": str(r.get("path_pattern", "")),
                    "policy": str(r.get("policy", "unknown")),
                    "default_route_mode": r.get("default_route_mode"),
                    "go_route_mode": r.get("go_route_mode"),
                }
                for r in folder_policy.get("rows", [])
                if isinstance(r, dict) and r.get("path_pattern")
            ],
            "apply_patterns": [
                str(r.get("path_pattern"))
                for r in folder_policy.get("rows", [])
                if isinstance(r, dict) and str(r.get("policy")) == "apply"
            ],
            "caution_patterns": [
                str(r.get("path_pattern"))
                for r in folder_policy.get("rows", [])
                if isinstance(r, dict) and str(r.get("policy")) == "caution"
            ],
            "forbid_patterns": [
                str(r.get("path_pattern"))
                for r in folder_policy.get("rows", [])
                if isinstance(r, dict) and str(r.get("policy")) == "forbid"
            ],
        },
        "observability": {
            "go_count": stats.get("go_count"),
            "watch_count": stats.get("watch_count"),
            "hold_count": stats.get("hold_count"),
            "go_ratio": stats.get("go_ratio"),
        },
        "promotion_gate": {
            "apply_go_enabled": apply_go_enabled,
            "apply_promotion_decision": str(apply_promotion.get("decision", "UNKNOWN")),
            "apply_promotion_reasons": apply_promotion.get("reasons", []),
            "readiness_block_applied": bool(dec.get("readiness_block_applied", False)),
            "readiness_block_checked_at_utc": dec.get("readiness_block_checked_at_utc"),
            "guard_applied": bool(dec.get("guard_applied", False)),
            "guard_reason": dec.get("guard_reason"),
        },
        "notes": [
            "Runtime config is generated from policy decision artifact; do not edit manually.",
            "If disable env is set to 1, force fallback to track_a_primary at runtime.",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "route_mode": route_mode,
                "pointer_enabled": pointer_enabled,
                "pointer_shadow": pointer_shadow,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
