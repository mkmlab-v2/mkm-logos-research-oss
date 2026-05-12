#!/usr/bin/env python3
"""Build weekly threshold policy artifact from prompt PoC KPI."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POC = ROOT / "reports" / "lens_music_prompt_poc_metric_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_threshold_policy_latest.json"


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poc-json", type=Path, default=DEFAULT_POC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-samples-floor", type=int, default=30)
    ap.add_argument("--style-delta-floor", type=float, default=0.30)
    ap.add_argument("--style-match-floor", type=float, default=0.67)
    args = ap.parse_args()

    poc = _read_json(args.poc_json)
    kpi = dict(poc.get("kpi") or {})
    targets = dict(poc.get("targets") or {})
    result = dict(poc.get("result") or {})

    samples = int(poc.get("samples_count") or 0)
    style_delta = float(kpi.get("style_delta_rate") or 0.0)
    style_match = float(kpi.get("overlay_style_match_rate") or 0.0)

    effective_min_samples = max(int(args.min_samples_floor), int(targets.get("min_samples") or 0))
    effective_style_delta = max(float(args.style_delta_floor), float(targets.get("style_delta_rate_min") or 0.0))
    effective_style_match = max(float(args.style_match_floor), float(targets.get("overlay_style_match_rate_min") or 0.0))

    checks = {
        "samples_pass": samples >= effective_min_samples,
        "style_delta_pass": style_delta >= effective_style_delta,
        "style_match_pass": style_match >= effective_style_match,
        "metric_runner_pass": bool(result.get("passed") is True),
    }
    policy_state = "GO" if all(checks.values()) else "WATCH"

    out = {
        "schema": "lens_music_prompt_poc_threshold_policy_v1",
        "generated_at_utc": _utc_now(),
        "source_poc_metric_json": str(args.poc_json).replace("\\", "/"),
        "policy_targets": {
            "min_samples": effective_min_samples,
            "style_delta_rate_min": round(effective_style_delta, 6),
            "overlay_style_match_rate_min": round(effective_style_match, 6),
        },
        "snapshot": {
            "samples_count": samples,
            "style_delta_rate": round(style_delta, 6),
            "overlay_style_match_rate": round(style_match, 6),
            "runner_state": str(result.get("state") or "UNKNOWN"),
        },
        "checks": checks,
        "state": policy_state,
        "advisory_only": True,
        "track": "B",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": policy_state, "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
