#!/usr/bin/env python3
"""Build S1 shadow gate decision from comparator and apply policy."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_COMPARATOR = ART / "lens_penalty_s1_shadow_comparator_latest.json"
DEFAULT_APPLY_POLICY = ART / "lens_penalty_apply_mode_policy_v1.json"
DEFAULT_OUT = ART / "lens_penalty_s1_shadow_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comparator-json", type=Path, default=DEFAULT_COMPARATOR)
    ap.add_argument("--apply-policy-json", type=Path, default=DEFAULT_APPLY_POLICY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-flip-candidates", type=int, default=1)
    args = ap.parse_args()

    comparator = _read_json(args.comparator_json)
    apply_policy = _read_json(args.apply_policy_json)
    summary = comparator.get("summary") if isinstance(comparator.get("summary"), dict) else {}

    simulated_gap = float(summary.get("simulated_strict_gap") or 0.0)
    flip_candidates = int(summary.get("flip_candidates") or 0)
    human_review_required = bool(apply_policy.get("human_review_required", True))

    checks = {
        "simulated_strict_gap_lt_zero": simulated_gap < 0.0,
        "flip_candidates_ready": flip_candidates >= int(args.min_flip_candidates),
        "human_review_required": human_review_required,
    }
    all_green = all(checks.values())
    decision = "GO_REVIEW" if all_green else "HOLD"

    out = {
        "schema": "lens_penalty_s1_shadow_gate_v1",
        "generated_at_utc": _now(),
        "decision": decision,
        "all_green": all_green,
        "checks": checks,
        "snapshot": {
            "simulated_strict_gap": simulated_gap,
            "flip_candidates": flip_candidates,
            "min_flip_candidates": int(args.min_flip_candidates),
        },
        "constraints": {
            "human_review_required": human_review_required,
            "auto_apply_enabled": False,
        },
        "inputs": {
            "comparator_json": str(args.comparator_json.resolve()).replace("\\", "/"),
            "apply_policy_json": str(args.apply_policy_json.resolve()).replace("\\", "/"),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"decision={decision}; all_green={all_green}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
