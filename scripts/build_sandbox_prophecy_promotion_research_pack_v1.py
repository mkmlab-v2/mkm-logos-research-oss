#!/usr/bin/env python3
"""SANDBOX promotion *research* pack — not Track A / not live trading."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "reports/sandbox_prophecy_panel_v1_latest.json"
DEFAULT_HOLDOUT = ROOT / "reports/sandbox_prophecy_holdout_report_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json"


def build_pack(
    panel: dict[str, Any],
    holdout: dict[str, Any] | None,
    *,
    min_panel_hit: float = 0.55,
) -> dict[str, Any]:
    holdout_pass = set(holdout.get("holdout_pass_target_ids") or []) if holdout else set()
    candidates: list[dict[str, Any]] = []
    for t in panel.get("targets") or []:
        if not t.get("ok"):
            continue
        tid = str(t.get("target_id") or "")
        if tid.endswith("_invert") or "_db0" in tid:
            continue
        try:
            hit = float(t.get("hit_rate"))
        except (TypeError, ValueError):
            continue
        if hit < min_panel_hit:
            continue
        if holdout_pass and tid not in holdout_pass:
            continue
        candidates.append(
            {
                "target_id": tid,
                "asset": t.get("asset"),
                "lens_profile": t.get("lens_profile"),
                "panel_hit_rate": hit,
                "holdout_stable": tid in holdout_pass if holdout_pass else None,
                "note_ko": "연구 후보만 — combined_all_passed·휴먼·본선 승격 별도.",
            }
        )

    candidates.sort(key=lambda x: (-float(x.get("panel_hit_rate") or 0), x.get("target_id") or ""))

    return {
        "schema": "sandbox_prophecy_promotion_research_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "track_a_auto_promotion": False,
        "live_trading": False,
        "policy": {
            "min_panel_hit": min_panel_hit,
            "require_holdout_pass": bool(holdout_pass),
            "exclude_invert_and_deadband_suffix": True,
        },
        "n_candidates": len(candidates),
        "candidates": candidates,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-panel-hit", type=float, default=0.55)
    args = ap.parse_args()
    if not args.panel_json.is_file():
        print(f"Missing panel: {args.panel_json}", file=__import__("sys").stderr)
        return 2
    panel = json.loads(args.panel_json.read_text(encoding="utf-8-sig"))
    holdout = None
    if args.holdout_json.is_file():
        holdout = json.loads(args.holdout_json.read_text(encoding="utf-8-sig"))
    pack = build_pack(panel, holdout, min_panel_hit=args.min_panel_hit)
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"candidates={pack['n_candidates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
