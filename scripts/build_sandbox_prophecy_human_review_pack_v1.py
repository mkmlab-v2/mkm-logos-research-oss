#!/usr/bin/env python3
"""Human-review pack for SANDBOX promotion (research_only — no auto Track A / live)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = ROOT / "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"
DEFAULT_PROMOTION = ROOT / "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json"
DEFAULT_ACCUMULATION = ROOT / "reports/sandbox_prophecy_accumulation_status_v1_latest.json"
DEFAULT_WATCHLIST = ROOT / "reports/sandbox_prophecy_watchlist_v1_latest.json"
DEFAULT_MAINLINE = ROOT / "docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_human_review_pack_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def build_pack(
    *,
    bridge: dict[str, Any] | None,
    promotion: dict[str, Any] | None,
    accumulation: dict[str, Any] | None,
    watchlist: dict[str, Any] | None,
    mainline: dict[str, Any] | None,
) -> dict[str, Any]:
    tiers = bridge or {}
    acc = accumulation or {}
    wl = watchlist or {}

    checklist = [
        "SANDBOX 증거만 검토 — prod btrack_prophecy_score_latest.json 자동 갱신 금지",
        "combined_all_passed·실매매 ON·Track A 자동 브리지 금지",
        "holdout_pass tier만 본선 후보 검토 권장(early/staging은 관측)",
        "본선 BTC v1_price_only 후보(JSON)와 별도 승격 절차",
    ]

    if acc.get("watchlist_gate_open"):
        checklist.append("full watchlist 게이트 충족 — 3일 streak 후보 확인")
    elif int(acc.get("days_until_watchlist_eligible") or 99) <= 1:
        checklist.append("내일 일일 체인 후 full watchlist 전환 가능")

    n_holdout = int(tiers.get("n_tier_holdout_pass") or 0)
    if n_holdout > 0:
        checklist.append(f"holdout_pass {n_holdout}건 — apply_prophecy_human_approval 별도 검토")

    return {
        "schema": "sandbox_prophecy_human_review_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "status": "AWAITING_HUMAN" if (tiers.get("n_total_draft_rows") or 0) else "NO_CANDIDATES",
        "runtime_constraints": {
            "prod_score_mutation": False,
            "live_trading": False,
            "track_b_to_a_auto_bridge": False,
        },
        "accumulation_summary": {
            "max_n_calendar_days": acc.get("max_n_calendar_days"),
            "days_until_watchlist_eligible": acc.get("days_until_watchlist_eligible"),
            "watchlist_gate_open": acc.get("watchlist_gate_open"),
            "next_milestone_ko": acc.get("next_milestone_ko"),
            "n_full_watchlist": acc.get("n_full_watchlist"),
            "n_early_watchlist": acc.get("n_early_watchlist"),
        },
        "watchlist_snapshot": {
            "candidates": wl.get("candidates") or [],
            "early_candidates": wl.get("early_candidates") or [],
        },
        "bridge_draft_summary": {
            "n_tier_holdout_pass": tiers.get("n_tier_holdout_pass"),
            "n_tier_early_watchlist": tiers.get("n_tier_early_watchlist"),
            "n_tier_panel_staging": tiers.get("n_tier_panel_staging"),
            "tier_holdout_pass": tiers.get("tier_holdout_pass") or [],
            "tier_early_watchlist": (tiers.get("tier_early_watchlist") or [])[:10],
            "tier_panel_staging": tiers.get("tier_panel_staging") or [],
            "recommended_next_human_action": tiers.get("recommended_next_human_action"),
        },
        "promotion_research_top5": (promotion.get("candidates") or [])[:5] if promotion else [],
        "mainline_candidate_reference": {
            "path": "docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json",
            "status": (mainline or {}).get("status"),
            "ensemble_profile": ((mainline or {}).get("btrack_stack") or {}).get("ensemble_profile"),
            "note_ko": "SANDBOX 초안이 본선 후보를 대체하지 않음",
        }
        if mainline
        else None,
        "human_review_checklist_ko": checklist,
        "evidence_refs": {
            "bridge_draft": "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json",
            "promotion_research": "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json",
            "accumulation_status": "reports/sandbox_prophecy_accumulation_status_v1_latest.json",
            "watchlist": "reports/sandbox_prophecy_watchlist_v1_latest.json",
            "ops_dashboard": "reports/sandbox_prophecy_ops_dashboard_v1_latest.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_pack(
        bridge=_load(DEFAULT_BRIDGE),
        promotion=_load(DEFAULT_PROMOTION),
        accumulation=_load(DEFAULT_ACCUMULATION),
        watchlist=_load(DEFAULT_WATCHLIST),
        mainline=_load(DEFAULT_MAINLINE),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"status={doc['status']} holdout_tier={doc['bridge_draft_summary']['n_tier_holdout_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
