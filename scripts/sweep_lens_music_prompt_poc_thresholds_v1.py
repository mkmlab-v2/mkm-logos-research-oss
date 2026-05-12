#!/usr/bin/env python3
"""Sweep prompt PoC threshold candidates and recommend a weekly policy."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POC = ROOT / "reports" / "lens_music_prompt_poc_metric_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_poc_threshold_sweep_latest.json"


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


def _parse_grid_float(raw: str) -> list[float]:
    vals = []
    for part in raw.split(","):
        s = part.strip()
        if not s:
            continue
        vals.append(float(s))
    return vals


def _parse_grid_int(raw: str) -> list[int]:
    vals = []
    for part in raw.split(","):
        s = part.strip()
        if not s:
            continue
        vals.append(int(s))
    return vals


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--poc-json", type=Path, default=DEFAULT_POC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-samples-grid", type=str, default="20,24,30,36,48")
    ap.add_argument("--style-delta-grid", type=str, default="0.30,0.35,0.40,0.50,0.60")
    ap.add_argument("--style-match-grid", type=str, default="0.67,0.75,0.85,0.90,0.95")
    args = ap.parse_args()

    poc = _read_json(args.poc_json)
    kpi = dict(poc.get("kpi") or {})
    samples_count = int(poc.get("samples_count") or 0)
    style_delta = float(kpi.get("style_delta_rate") or 0.0)
    style_match = float(kpi.get("overlay_style_match_rate") or 0.0)

    min_samples_grid = _parse_grid_int(args.min_samples_grid)
    style_delta_grid = _parse_grid_float(args.style_delta_grid)
    style_match_grid = _parse_grid_float(args.style_match_grid)

    candidates: list[dict[str, Any]] = []
    for s in min_samples_grid:
        for d in style_delta_grid:
            for m in style_match_grid:
                samples_pass = samples_count >= s
                style_delta_pass = style_delta >= d
                style_match_pass = style_match >= m
                passed = samples_pass and style_delta_pass and style_match_pass
                strictness = round((s / max(samples_count, 1)) + d + m, 6)
                candidates.append(
                    {
                        "min_samples": s,
                        "style_delta_rate_min": d,
                        "overlay_style_match_rate_min": m,
                        "checks": {
                            "samples_pass": samples_pass,
                            "style_delta_pass": style_delta_pass,
                            "style_match_pass": style_match_pass,
                        },
                        "passed": passed,
                        "strictness_score": strictness,
                    }
                )

    passing = [c for c in candidates if c["passed"]]
    if passing:
        recommended = max(passing, key=lambda c: (c["strictness_score"], c["min_samples"]))
        decision = "GO_RECOMMENDED"
    else:
        recommended = {
            "min_samples": min_samples_grid[0] if min_samples_grid else 30,
            "style_delta_rate_min": style_delta_grid[0] if style_delta_grid else 0.30,
            "overlay_style_match_rate_min": style_match_grid[0] if style_match_grid else 0.67,
            "fallback_reason": "no_passing_candidate",
        }
        decision = "WATCH_NO_PASSING_CANDIDATE"

    out = {
        "schema": "lens_music_prompt_poc_threshold_sweep_v1",
        "generated_at_utc": _utc_now(),
        "source_poc_metric_json": str(args.poc_json).replace("\\", "/"),
        "snapshot": {
            "samples_count": samples_count,
            "style_delta_rate": style_delta,
            "overlay_style_match_rate": style_match,
        },
        "grid": {
            "min_samples": min_samples_grid,
            "style_delta_rate_min": style_delta_grid,
            "overlay_style_match_rate_min": style_match_grid,
        },
        "summary": {
            "candidate_count": len(candidates),
            "passing_count": len(passing),
            "decision": decision,
        },
        "recommended_policy": recommended,
        "top_passing": sorted(passing, key=lambda c: c["strictness_score"], reverse=True)[:5],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
