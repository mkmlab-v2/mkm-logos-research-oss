#!/usr/bin/env python3
"""Build S1 promotion review packet from latest artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


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
    ap.add_argument("--weekly-json", type=Path, default=ART / "lens_penalty_shadow_weekly_report_latest.json")
    ap.add_argument("--fail-reason-json", type=Path, default=ART / "lens_penalty_shadow_fail_reason_report_latest.json")
    ap.add_argument("--sweep-json", type=Path, default=ART / "lens_penalty_direction_sensitivity_sweep_latest.json")
    ap.add_argument("--comparator-json", type=Path, default=ART / "lens_penalty_s1_shadow_comparator_latest.json")
    ap.add_argument("--gate-json", type=Path, default=ART / "lens_penalty_s1_shadow_gate_latest.json")
    ap.add_argument("--streak-json", type=Path, default=ART / "lens_penalty_s1_shadow_streak_gate_latest.json")
    ap.add_argument("--out", type=Path, default=ART / "lens_penalty_s1_promotion_review_packet_latest.json")
    args = ap.parse_args()

    weekly = _read_json(args.weekly_json)
    fail_reason = _read_json(args.fail_reason_json)
    sweep = _read_json(args.sweep_json)
    comparator = _read_json(args.comparator_json)
    gate = _read_json(args.gate_json)
    streak = _read_json(args.streak_json)

    packet = {
        "schema": "lens_penalty_s1_promotion_review_packet_v1",
        "generated_at_utc": _now(),
        "decision_hint": str((streak.get("decision") or gate.get("decision") or "HOLD")),
        "summary": {
            "weekly_strict_gap": float((weekly.get("summary") or {}).get("strict_gap") or 0.0),
            "simulated_strict_gap": float((comparator.get("summary") or {}).get("simulated_strict_gap") or 0.0),
            "flip_candidates": int((comparator.get("summary") or {}).get("flip_candidates") or 0),
            "top_fail_reason": str((fail_reason.get("summary") or {}).get("top_reason_code") or "NONE"),
            "streak_go_days": int((streak.get("snapshot") or {}).get("current_go_streak") or 0),
        },
        "artifacts": {
            "weekly": weekly,
            "fail_reason": fail_reason,
            "sweep": sweep,
            "comparator": comparator,
            "gate": gate,
            "streak": streak,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"decision_hint={packet['decision_hint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
