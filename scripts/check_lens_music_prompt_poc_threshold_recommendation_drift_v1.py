#!/usr/bin/env python3
"""Check recommendation drift against previous run and emit alert artifact."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_RECOMMENDED = ART / "lens_music_prompt_poc_threshold_recommended_latest.json"
DEFAULT_STATE = ART / "lens_music_prompt_poc_threshold_recommendation_drift_state_latest.json"
DEFAULT_LOG = ROOT / "reports" / "lens_music_prompt_poc_threshold_recommendation_drift_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recommended-json", type=Path, default=DEFAULT_RECOMMENDED)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--samples-delta-max", type=int, default=12)
    ap.add_argument("--style-delta-min-delta-max", type=float, default=0.15)
    ap.add_argument("--style-match-min-delta-max", type=float, default=0.15)
    args = ap.parse_args()

    rec = _read_json(args.recommended_json)
    prev = _read_json(args.state_json)
    targets = dict(rec.get("policy_targets") or {})
    prev_targets = dict(prev.get("current_policy_targets") or {})

    cur_samples = int(_num(targets.get("min_samples"), 30))
    cur_style_delta = _num(targets.get("style_delta_rate_min"), 0.30)
    cur_style_match = _num(targets.get("overlay_style_match_rate_min"), 0.67)

    had_prev = bool(prev_targets)
    prev_samples = int(_num(prev_targets.get("min_samples"), cur_samples))
    prev_style_delta = _num(prev_targets.get("style_delta_rate_min"), cur_style_delta)
    prev_style_match = _num(prev_targets.get("overlay_style_match_rate_min"), cur_style_match)

    deltas = {
        "min_samples_delta": cur_samples - prev_samples,
        "style_delta_rate_min_delta": round(cur_style_delta - prev_style_delta, 6),
        "overlay_style_match_rate_min_delta": round(cur_style_match - prev_style_match, 6),
    }
    checks = {
        "samples_delta_within_bound": abs(deltas["min_samples_delta"]) <= int(args.samples_delta_max),
        "style_delta_min_delta_within_bound": abs(deltas["style_delta_rate_min_delta"]) <= float(args.style_delta_min_delta_max),
        "style_match_min_delta_within_bound": abs(deltas["overlay_style_match_rate_min_delta"]) <= float(args.style_match_min_delta_max),
    }

    if not had_prev:
        state = "INIT"
        reason = "no_previous_state"
    else:
        state = "GO" if all(checks.values()) else "WATCH"
        reason = "within_bounds" if state == "GO" else "drift_exceeds_bounds"

    out = {
        "schema": "lens_music_prompt_poc_threshold_recommendation_drift_v1",
        "generated_at_utc": _utc_now(),
        "source_recommended_json": str(args.recommended_json).replace("\\", "/"),
        "state": state,
        "reason": reason,
        "had_previous_state": had_prev,
        "bounds": {
            "samples_delta_max": int(args.samples_delta_max),
            "style_delta_min_delta_max": float(args.style_delta_min_delta_max),
            "style_match_min_delta_max": float(args.style_match_min_delta_max),
        },
        "current_policy_targets": {
            "min_samples": cur_samples,
            "style_delta_rate_min": cur_style_delta,
            "overlay_style_match_rate_min": cur_style_match,
        },
        "previous_policy_targets": {
            "min_samples": prev_samples,
            "style_delta_rate_min": prev_style_delta,
            "overlay_style_match_rate_min": prev_style_match,
        },
        "deltas": deltas,
        "checks": checks,
        "advisory_only": True,
        "track": "B",
    }

    args.state_json.parent.mkdir(parents=True, exist_ok=True)
    args.state_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_jsonl(
        args.log_jsonl,
        {
            "ts": out["generated_at_utc"],
            "state": state,
            "reason": reason,
            "deltas": deltas,
            "checks": checks,
        },
    )
    print(json.dumps({"ok": True, "state": state, "reason": reason, "out": str(args.state_json.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
