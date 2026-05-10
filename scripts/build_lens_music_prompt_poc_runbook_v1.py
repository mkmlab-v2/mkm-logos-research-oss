#!/usr/bin/env python3
"""Build M28 runbook recommendations from prompt PoC metric status."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POC = ROOT / "reports" / "lens_music_prompt_poc_metric_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_runbook_latest.json"


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
    args = ap.parse_args()

    poc = _read_json(args.poc_json)
    result = dict(poc.get("result") or {})
    kpi = dict(poc.get("kpi") or {})
    targets = dict(poc.get("targets") or {})

    state = str(result.get("state") or "UNKNOWN")
    style_delta = float(kpi.get("style_delta_rate") or 0.0)
    style_match = float(kpi.get("overlay_style_match_rate") or 0.0)
    min_delta = float(targets.get("style_delta_rate_min") or 0.30)
    min_match = float(targets.get("overlay_style_match_rate_min") or 0.67)

    recommendations: list[dict[str, Any]] = []
    if state == "WATCH":
        if style_delta < min_delta:
            recommendations.append(
                {
                    "cause": "style_delta_below_target",
                    "action": "Increase short-form control emphasis in overlay wording and re-run paired PoC set.",
                    "priority": "high",
                }
            )
        if style_match < min_match:
            recommendations.append(
                {
                    "cause": "style_match_below_target",
                    "action": "Refine calm_guarded lexical constraints and expand WATCH-style fixtures before re-eval.",
                    "priority": "high",
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "cause": "watch_without_single_kpi_failure",
                    "action": "Inspect per-row drift outliers and regenerate baseline/overlay pairset with fixed prompts.",
                    "priority": "medium",
                }
            )
    else:
        recommendations.append(
            {
                "cause": "poc_go_state",
                "action": "Keep current profile and continue weekly regression monitoring.",
                "priority": "low",
            }
        )

    out = {
        "schema": "lens_music_prompt_poc_runbook_v1",
        "generated_at_utc": _utc_now(),
        "source_schema": poc.get("schema"),
        "state": state,
        "kpi_snapshot": {
            "style_delta_rate": style_delta,
            "overlay_style_match_rate": style_match,
            "style_delta_rate_min": min_delta,
            "overlay_style_match_rate_min": min_match,
        },
        "recommendations": recommendations,
        "advisory_only": True,
        "track": "B",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": state, "recommendation_count": len(recommendations), "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
