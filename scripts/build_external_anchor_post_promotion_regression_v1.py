#!/usr/bin/env python3
"""Post-promotion regression check for external anchor operating policy."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROMOTED = ART / "external_bible_anchor_tier1_promoted_latest.json"
DEFAULT_SHADOW = ART / "external_bible_anchor_shadow_rehearsal_latest.json"
DEFAULT_LAYER5 = ART / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_PREFLIGHT = ART / "emotion_state_live_preflight_gate_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_post_promotion_regression_latest.json"


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
    ap.add_argument("--promoted-json", type=Path, default=DEFAULT_PROMOTED)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_LAYER5)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--min-shadow-pass-ratio", type=float, default=0.80)
    ap.add_argument("--max-layer5-fpr", type=float, default=0.05)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    promoted = _read_json(args.promoted_json)
    shadow = _read_json(args.shadow_json)
    layer5 = _read_json(args.layer5_json)
    preflight = _read_json(args.preflight_json)

    promoted_status = str(promoted.get("status") or "")
    promoted_ok = promoted_status in {"PROMOTED_TIER1_CANDIDATES", "PROMOTED_TIER1_CANDIDATES_LATCHED"}
    shadow_summary = shadow.get("summary") if isinstance(shadow.get("summary"), dict) else {}
    shadow_pass_ratio = float(
        shadow_summary.get("promotion_shadow_pass_ratio")
        if shadow_summary.get("promotion_shadow_pass_ratio") is not None
        else (shadow_summary.get("shadow_pass_ratio") or 0.0)
    )
    layer5_fpr = float(((layer5.get("metrics") or {}).get("false_positive_rate")) or 0.0)
    preflight_go = str(preflight.get("decision") or "") == "GO_LIVE_CANDIDATE"

    checks = {
        "promoted_present": promoted_ok,
        "shadow_pass_ratio_ok": shadow_pass_ratio >= float(args.min_shadow_pass_ratio),
        "layer5_fpr_ok": layer5_fpr <= float(args.max_layer5_fpr),
        "preflight_go": preflight_go,
    }
    passed = all(checks.values())
    out = {
        "schema": "external_bible_anchor_post_promotion_regression_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "promoted_json": str(args.promoted_json).replace("\\", "/"),
            "shadow_json": str(args.shadow_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
            "preflight_json": str(args.preflight_json).replace("\\", "/"),
        },
        "thresholds": {
            "min_shadow_pass_ratio": float(args.min_shadow_pass_ratio),
            "max_layer5_fpr": float(args.max_layer5_fpr),
        },
        "current": {
            "shadow_pass_ratio": shadow_pass_ratio,
            "shadow_pass_ratio_source": (
                "promotion_shadow_pass_ratio"
                if shadow_summary.get("promotion_shadow_pass_ratio") is not None
                else "shadow_pass_ratio"
            ),
            "layer5_fpr": layer5_fpr,
            "preflight_decision": preflight.get("decision"),
        },
        "checks": checks,
        "status": "PASS" if passed else "FAIL",
        "recommended_action": "keep_adopt_limited" if passed else "rollback_to_monitor_only",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "status": out["status"],
                "recommended_action": out["recommended_action"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
