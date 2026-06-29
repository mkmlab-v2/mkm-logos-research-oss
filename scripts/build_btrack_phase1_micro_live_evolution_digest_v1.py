#!/usr/bin/env python3
"""[HYPO] Daily digest: B-track Type-A micro-live prediction vs realized (evolution telemetry)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_btrack_btc_direction_error_spike_v1 import _hit_rate, _load

SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
SIGNAL_LOG = ROOT / "reports/btrack_phase1_micro_live_signal_log_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/btrack_phase1_micro_live_evolution_digest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _btc_rows(score: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        r
        for r in (score.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "btc"
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=SCORE)
    ap.add_argument("--signal-log", type=Path, default=SIGNAL_LOG)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-days", type=int, default=15)
    args = ap.parse_args(argv)

    score = _load(args.score_json)
    rows = sorted(_btc_rows(score), key=lambda r: str(r.get("eval_date") or ""))
    window = rows[-args.window_days :] if args.window_days > 0 else rows
    scored = [r for r in window if r.get("actual_direction")]
    hr = _hit_rate(scored) if scored else {"price_directional_hit_rate": None, "n_evaluated": 0}

    misses = []
    for r in scored:
        pred = str(r.get("predicted_direction") or "").lower()
        act = str(r.get("actual_direction") or "").lower()
        if pred != act and pred != "neutral":
            misses.append(
                {
                    "eval_date": r.get("eval_date"),
                    "predicted": pred,
                    "actual": act,
                    "typea_guard_applied": bool(r.get("typea_guard_applied")),
                }
            )

    latest = rows[-1] if rows else {}
    signal_tail = []
    if args.signal_log.is_file():
        for line in args.signal_log.read_text(encoding="utf-8").splitlines()[-5:]:
            line = line.strip()
            if line:
                try:
                    signal_tail.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    doc = {
        "schema": "btrack_phase1_micro_live_evolution_digest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "window_days": args.window_days,
        "btc_panel": {
            "n_rows": len(window),
            "n_scored": len(scored),
            "hit_rate": hr.get("price_directional_hit_rate"),
            "n_hits": hr.get("price_hits"),
        },
        "latest_signal": {
            "eval_date": latest.get("eval_date"),
            "predicted_direction": latest.get("predicted_direction"),
            "actual_direction": latest.get("actual_direction"),
            "typea_guard_applied": latest.get("typea_guard_applied"),
        },
        "recent_misses": misses[-5:],
        "signal_log_tail": signal_tail,
        "evolution_hint": (
            "Compare live fills/PnL vs side_hint in signal_log; tune Type-A score_lt only on holdout evidence."
            if misses
            else "Panel stable; continue micro-live telemetry."
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"hit_rate={hr.get('price_directional_hit_rate')} n_scored={len(scored)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
