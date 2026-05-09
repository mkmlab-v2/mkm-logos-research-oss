#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_rule_school_mkm_4d_v1 import (  # noqa: E402
    apply_myeongni_conflict_arbitration_v1,
    load_myeongni_conflict_arbitration_v1,
)

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_conflict_arbitration_edgecases_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _operational_action(meta: dict[str, Any]) -> str:
    # Operational adapter: convert policy label into explicit action.
    label = str(meta.get("vector_policy_label", "WATCH"))
    if label == "GO_SPECIAL_CONTROLLED":
        return "GO"
    if bool(meta.get("jogoo_triggered")) and float(meta.get("k_multiplier_applied", 1.0)) > 1.0:
        return "HOLD"
    return "WATCH"


def _run_case(case: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    out, meta = apply_myeongni_conflict_arbitration_v1(
        case["vector"],
        ohang_surface=case["surface"],
        ohang_jijangan=case["jijangan"],
        policy=policy,
    )
    action = _operational_action(meta)
    return {
        "case_id": case["case_id"],
        "expected_action": case["expected_action"],
        "actual_action": action,
        "pass": action == case["expected_action"],
        "vector_arbitrated": out,
        "meta": meta,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify extreme edgecases for myeongni conflict arbitration.")
    ap.add_argument("--policy-json", type=Path, default=ROOT / "data" / "myeongni" / "myeongni_conflict_arbitration_v1.json")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = load_myeongni_conflict_arbitration_v1(args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json)

    # Case A: Extreme jogoo => HOLD operational guard.
    c_hold = {
        "case_id": "extreme_jogoo_hold_guard",
        "expected_action": "HOLD",
        "vector": {"S": 0.20, "L": 0.08, "K": 0.24, "M": 0.48},
        "surface": {"wood_strength": 0.0, "fire_strength": 1.0, "earth_strength": 0.0, "metal_strength": 0.0, "water_strength": 0.0},
        "jijangan": {"wood_strength": 0.0, "fire_strength": 0.8, "earth_strength": 0.2, "metal_strength": 0.0, "water_strength": 0.0},
    }
    # Case B: Stable band GO — widen only for this case verification.
    go_policy = json.loads(json.dumps(policy))
    go_policy["arbitration_rules"]["rule_3_gyukguk_vs_4d_vector"]["stability_band"] = {
        "l_min": 0.0,
        "l_max": 1.0,
        "k_min": 0.0,
        "k_max": 1.0,
    }
    c_go = {
        "case_id": "stable_band_go",
        "expected_action": "GO",
        "vector": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        "surface": {"wood_strength": 0.2, "fire_strength": 0.2, "earth_strength": 0.2, "metal_strength": 0.2, "water_strength": 0.2},
        "jijangan": {"wood_strength": 0.2, "fire_strength": 0.2, "earth_strength": 0.2, "metal_strength": 0.2, "water_strength": 0.2},
    }
    # Case C: Normal neutral => WATCH.
    c_watch = {
        "case_id": "neutral_watch",
        "expected_action": "WATCH",
        "vector": {"S": 0.24, "L": 0.18, "K": 0.18, "M": 0.4},
        "surface": {"wood_strength": 0.2, "fire_strength": 0.2, "earth_strength": 0.2, "metal_strength": 0.2, "water_strength": 0.2},
        "jijangan": {"wood_strength": 0.2, "fire_strength": 0.2, "earth_strength": 0.2, "metal_strength": 0.2, "water_strength": 0.2},
    }

    results = [
        _run_case(c_hold, policy),
        _run_case(c_go, go_policy),
        _run_case(c_watch, policy),
    ]
    passed = all(bool(x.get("pass")) for x in results)
    out = {
        "schema": "myeongni_conflict_arbitration_edgecases_v1",
        "generated_at_utc": _now(),
        "policy_path": str((args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json).resolve()),
        "passed": passed,
        "results": results,
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "passed": passed, "out": str(out_path)}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
