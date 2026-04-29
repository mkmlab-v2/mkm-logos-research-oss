#!/usr/bin/env python3
"""Build trend snapshot for Sasang supplemental insight score.

Policy: non-gating supporting evidence only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SCORE = ART / "sasang_supplemental_insight_score_latest.json"
DEFAULT_PREV_TREND = ART / "sasang_supplemental_insight_trend_latest.json"
DEFAULT_OUT = ART / "sasang_supplemental_insight_trend_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _trend_status(delta: float) -> str:
    if delta >= 0.02:
        return "UP"
    if delta <= -0.02:
        return "DOWN"
    return "STABLE"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--prev-trend", type=Path, default=DEFAULT_PREV_TREND)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score_doc = _read(args.score)
    if not isinstance(score_doc, dict):
        print(f"ERROR: missing supplemental score artifact: {args.score}")
        return 2

    prev_doc = _read(args.prev_trend)

    current = float(((score_doc.get("supplemental_score") or {}).get("value") or 0.0))
    previous = (
        float((prev_doc or {}).get("current_value")) if isinstance(prev_doc, dict) else None
    )
    delta = current - previous if previous is not None else 0.0
    trend = _trend_status(delta)
    alert = delta <= -0.08

    payload = {
        "schema": "sasang_supplemental_insight_trend_v1",
        "generated_at_utc": _now(),
        "non_gating_policy": True,
        "score_artifact": str(args.score.resolve()),
        "current_value": round(current, 6),
        "previous_value": round(previous, 6) if previous is not None else None,
        "delta": round(delta, 6),
        "trend_status": trend,
        "alert": alert,
        "impact_on_go_no_go": "none_non_gating",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"trend_status={trend}, alert={alert}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
