#!/usr/bin/env python3
"""Promote sweep `best` row into a recommended-threshold artifact for operators / alert CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", required=True, help="Output of sweep_aramaic_mvp_alert_thresholds_v1.py")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/aramaic_mvp_alert_threshold_recommended_latest.json",
    )
    a = ap.parse_args()

    sp = Path(a.sweep_json)
    if not sp.is_absolute():
        sp = ROOT / sp
    op = Path(a.output_json)
    if not op.is_absolute():
        op = ROOT / op

    sweep = _load(sp)
    if sweep.get("schema") != "aramaic_mvp_alert_threshold_sweep_v1":
        raise SystemExit("sweep-json must be aramaic_mvp_alert_threshold_sweep_v1")

    best = sweep.get("best")
    if not isinstance(best, dict) or not best:
        raise SystemExit("sweep-json missing best")

    rec = {
        "conflict_alert": float(best["conflict_alert"]),
        "conflict_critical": float(best["conflict_critical"]),
        "streak_min": int(best["streak_min"]),
    }

    doc: dict[str, Any] = {
        "schema": "aramaic_mvp_alert_threshold_recommended_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "source_sweep_json": str(sp),
        "recommended": rec,
        "sweep_score_proxy": best.get("score_proxy"),
        "sweep_end_severity": best.get("end_severity"),
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
