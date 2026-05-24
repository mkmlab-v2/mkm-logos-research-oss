#!/usr/bin/env python3
"""Single SANDBOX ops dashboard JSON (health, watchlist, bridge, brief slice)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEALTH = ROOT / "reports/sandbox_prophecy_health_v1_latest.json"
DEFAULT_WATCHLIST = ROOT / "reports/sandbox_prophecy_watchlist_v1_latest.json"
DEFAULT_BRIDGE = ROOT / "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"
DEFAULT_BRIEF = ROOT / "reports/sandbox_prophecy_brief_v1_latest.json"
DEFAULT_HOLDOUT = ROOT / "reports/sandbox_prophecy_holdout_report_v1_latest.json"
DEFAULT_CHAIN = ROOT / "reports/sandbox_prophecy_daily_chain_v1_latest.json"
DEFAULT_ACCUMULATION = ROOT / "reports/sandbox_prophecy_accumulation_status_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_ops_dashboard_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def build_dashboard(
    *,
    health: dict[str, Any] | None,
    watchlist: dict[str, Any] | None,
    bridge: dict[str, Any] | None,
    brief: dict[str, Any] | None,
    holdout: dict[str, Any] | None,
    chain: dict[str, Any] | None,
    accumulation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prog = (health or {}).get("checks", {}).get("rollup_progress", {})
    acc = accumulation or {}
    wl_cands = (watchlist or {}).get("candidates") or []
    early = (watchlist or {}).get("early_candidates") or []

    top3 = []
    for t in (brief or {}).get("leaderboard_top5") or []:
        if isinstance(t, dict):
            top3.append(t)
        if len(top3) >= 3:
            break

    return {
        "schema": "sandbox_prophecy_ops_dashboard_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "health_ok": (health or {}).get("ok"),
        "chain_ok": (chain or {}).get("ok"),
        "n_targets": (chain or {}).get("n_targets"),
        "max_calendar_days": acc.get("max_n_calendar_days") or prog.get("max_n_calendar_days"),
        "days_until_watchlist_eligible": acc.get("days_until_watchlist_eligible"),
        "next_milestone_ko": acc.get("next_milestone_ko"),
        "watchlist_ready": acc.get("watchlist_gate_open") or prog.get("watchlist_ready"),
        "n_watchlist_candidates": len(wl_cands),
        "n_early_watchlist": len(early),
        "n_holdout_pass": (holdout or {}).get("n_holdout_pass"),
        "bridge_tiers": {
            "holdout_pass": (bridge or {}).get("n_tier_holdout_pass"),
            "early_watchlist": (bridge or {}).get("n_tier_early_watchlist"),
            "panel_staging": (bridge or {}).get("n_tier_panel_staging"),
        },
        "recommended_next_human_action": (bridge or {}).get("recommended_next_human_action")
        or (health or {}).get("recommended_next"),
        "leaderboard_top3": top3,
        "brief_lines_ko": (brief or {}).get("brief_lines_ko") or [],
        "evidence_refs": {
            "health": "reports/sandbox_prophecy_health_v1_latest.json",
            "watchlist": "reports/sandbox_prophecy_watchlist_v1_latest.json",
            "bridge_draft": "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json",
            "brief": "reports/sandbox_prophecy_brief_v1_latest.json",
            "holdout": "reports/sandbox_prophecy_holdout_report_v1_latest.json",
            "chain": "reports/sandbox_prophecy_daily_chain_v1_latest.json",
            "accumulation_status": "reports/sandbox_prophecy_accumulation_status_v1_latest.json",
            "evidence_manifest": "reports/sandbox_prophecy_evidence_manifest_v1_latest.json",
        },
        "accumulation_note_ko": acc.get("note_ko"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_dashboard(
        health=_load(DEFAULT_HEALTH),
        watchlist=_load(DEFAULT_WATCHLIST),
        bridge=_load(DEFAULT_BRIDGE),
        brief=_load(DEFAULT_BRIEF),
        holdout=_load(DEFAULT_HOLDOUT),
        chain=_load(DEFAULT_CHAIN),
        accumulation=_load(DEFAULT_ACCUMULATION),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"health_ok={doc['health_ok']} max_days={doc['max_calendar_days']} "
        f"early={doc['n_early_watchlist']} holdout_pass={doc['n_holdout_pass']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
