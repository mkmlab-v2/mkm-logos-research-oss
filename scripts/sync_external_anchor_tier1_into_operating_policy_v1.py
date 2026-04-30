#!/usr/bin/env python3
"""Sync promoted Tier1 anchor result into operating policy artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_TIERING = ART / "external_bible_anchor_tiering_latest.json"
DEFAULT_PROMOTED = ART / "external_bible_anchor_tier1_promoted_latest.json"
DEFAULT_REGRESSION = ART / "external_bible_anchor_post_promotion_regression_latest.json"
DEFAULT_SUSTAIN = ART / "external_bible_anchor_promotion_sustain_gate_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_operating_policy_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tiering-json", type=Path, default=DEFAULT_TIERING)
    ap.add_argument("--promoted-json", type=Path, default=DEFAULT_PROMOTED)
    ap.add_argument("--regression-json", type=Path, default=DEFAULT_REGRESSION)
    ap.add_argument("--sustain-json", type=Path, default=DEFAULT_SUSTAIN)
    ap.add_argument("--strict-pass-streak-threshold", type=int, default=6)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tiering = _read_json(args.tiering_json)
    promoted = _read_json(args.promoted_json)
    regression = _read_json(args.regression_json)
    sustain = _read_json(args.sustain_json)

    base_action = str(tiering.get("policy_action") or "monitor_only").lower()
    promoted_status = str(promoted.get("status") or "")
    promoted_labels = promoted.get("promoted_labels") if isinstance(promoted.get("promoted_labels"), list) else []

    effective_action = (
        "adopt_limited"
        if promoted_status in {"PROMOTED_TIER1_CANDIDATES", "PROMOTED_TIER1_CANDIDATES_LATCHED"} and len(promoted_labels) > 0
        else base_action
    )
    regression_status = str(regression.get("status") or "")
    regression_action = str(regression.get("recommended_action") or "")
    if regression_status == "FAIL" or regression_action == "rollback_to_monitor_only":
        effective_action = "monitor_only"

    sustain_status = str(sustain.get("status") or "")
    sustain_current = sustain.get("current") if isinstance(sustain.get("current"), dict) else {}
    sustain_pass_streak = int(sustain_current.get("pass_streak") or 0)
    sustain_fail_streak = int(sustain_current.get("fail_streak") or 0)
    sustain_override = "none"
    strict_threshold = max(1, int(args.strict_pass_streak_threshold))
    if sustain_status == "DOWNGRADE_TRIGGER":
        effective_action = "monitor_only"
        sustain_override = "force_monitor_only_by_sustain_gate"
    elif sustain_status == "MATURE" and effective_action == "adopt_limited":
        if sustain_pass_streak >= strict_threshold:
            effective_action = "adopt_limited_strict"
            sustain_override = "mature_upgrade_to_adopt_limited_strict"
        else:
            sustain_override = "mature_keep_adopt_limited"

    out = {
        "schema": "external_bible_anchor_operating_policy_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "tiering_json": str(args.tiering_json).replace("\\", "/"),
            "promoted_json": str(args.promoted_json).replace("\\", "/"),
            "regression_json": str(args.regression_json).replace("\\", "/"),
            "sustain_json": str(args.sustain_json).replace("\\", "/"),
        },
        "base_action": base_action,
        "effective_action": effective_action,
        "promoted_status": promoted_status,
        "promoted_labels": promoted_labels,
        "regression_status": regression_status,
        "regression_action": regression_action,
        "sustain_status": sustain_status,
        "sustain_pass_streak": sustain_pass_streak,
        "sustain_fail_streak": sustain_fail_streak,
        "sustain_override": sustain_override,
        "strict_pass_streak_threshold": strict_threshold,
        "policy_stage": (
            "strict"
            if effective_action == "adopt_limited_strict"
            else ("limited" if effective_action == "adopt_limited" else "monitor")
        ),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "effective_action": effective_action,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
