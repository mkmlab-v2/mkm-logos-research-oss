#!/usr/bin/env python3
"""Build a compact dashboard for daily lens penalty shadow status."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_DAILY = ART / "lens_penalty_daily_latest.json"
DEFAULT_STATE = ART / "lens_penalty_shadow_state_latest.json"
DEFAULT_OUT = ART / "lens_penalty_shadow_dashboard_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-json", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    daily = _read_json(args.daily_json)
    state = _read_json(args.state_json)

    recs = daily.get("recommendations") if isinstance(daily.get("recommendations"), list) else []
    state_map = state.get("lens_state") if isinstance(state.get("lens_state"), dict) else {}

    per_lens: list[dict[str, Any]] = []
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        lid = str(rec.get("lens_id") or "")
        if not lid:
            continue
        st = state_map.get(lid) if isinstance(state_map.get(lid), dict) else {}
        per_lens.append(
            {
                "lens_id": lid,
                "events": int(rec.get("events") or 0),
                "fail_rate": float(rec.get("fail_rate") or 0.0),
                "proposed_multiplier": float(rec.get("proposed_multiplier") or 1.0),
                "delta": float(rec.get("delta") or 0.0),
                "reason": str(rec.get("reason") or ""),
                "cooldown_left": int(st.get("cooldown_left") or 0),
            }
        )

    summary = daily.get("summary") if isinstance(daily.get("summary"), dict) else {}
    out = {
        "schema": "lens_penalty_shadow_dashboard_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "daily_json": str(args.daily_json.resolve()).replace("\\", "/"),
            "state_json": str(args.state_json.resolve()).replace("\\", "/"),
        },
        "mode": str(daily.get("mode") or ""),
        "applied": bool(daily.get("applied")),
        "summary": {
            "lenses_evaluated": int(summary.get("lenses_evaluated") or 0),
            "recommendations_with_penalty": int(summary.get("recommendations_with_penalty") or 0),
            "recommendations_with_recovery": int(summary.get("recommendations_with_recovery") or 0),
        },
        "per_lens": per_lens,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"lenses={len(per_lens)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
