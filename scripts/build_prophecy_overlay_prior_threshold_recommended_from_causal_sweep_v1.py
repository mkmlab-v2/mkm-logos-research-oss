#!/usr/bin/env python3
"""Build recommended prior-return overlay threshold from causal sweep artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = ROOT / "docs" / "final" / "artifacts" / "prophecy_causal_threshold_sweep_v1_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_overlay_prior_threshold_recommended_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Recommend overlay prior-return threshold from causal sweep best candidate.")
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sweep_path = args.sweep_json if args.sweep_json.is_absolute() else ROOT / args.sweep_json
    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    sweep = _load(sweep_path)
    best = sweep.get("best_candidate") or {}
    low_thr = best.get("low_thr")
    if low_thr is None:
        raise SystemExit("best_candidate.low_thr missing in sweep artifact")

    payload = {
        "schema": "prophecy_overlay_prior_threshold_recommended_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "recommended_prior_return_threshold": float(low_thr),
        "rationale": "Selected from prophecy_causal_threshold_sweep_v1 best_candidate.low_thr (causal no-lookahead).",
        "source_summary": str(sweep_path),
        "score_snapshot": str(score_path),
        "not_live_routing": True,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"recommended_prior_return_threshold: {payload['recommended_prior_return_threshold']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
