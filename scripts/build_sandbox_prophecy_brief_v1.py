#!/usr/bin/env python3
"""Build operator brief from latest sandbox panel (research_only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "reports/sandbox_prophecy_panel_v1_latest.json"
DEFAULT_ROLLUP = ROOT / "reports/sandbox_prophecy_rollup_v1_latest.json"
DEFAULT_PROMOTION = ROOT / "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json"
DEFAULT_BRIDGE_DRAFT = ROOT / "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_brief_v1_latest.json"


def _rank_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for t in targets:
        if not t.get("ok"):
            continue
        hit = t.get("hit_rate")
        if hit is None:
            continue
        scored.append({**t, "_hit": float(hit)})
    scored.sort(key=lambda x: (-x["_hit"], str(x.get("target_id") or "")))
    return scored


def build_brief(
    panel: dict[str, Any],
    rollup: dict[str, Any] | None = None,
    promotion: dict[str, Any] | None = None,
    bridge_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    targets = panel.get("targets") if isinstance(panel.get("targets"), list) else []
    ranked = _rank_targets(targets)
    top = [
        {
            "target_id": t.get("target_id"),
            "hit_rate": t.get("hit_rate"),
            "n_evaluated": t.get("n_evaluated"),
        }
        for t in ranked[:5]
    ]
    bottom = [
        {
            "target_id": t.get("target_id"),
            "hit_rate": t.get("hit_rate"),
            "n_evaluated": t.get("n_evaluated"),
        }
        for t in ranked[-5:]
    ]

    funding = next((t for t in targets if t.get("target_id") == "btc_phase3_funding_skew"), None)
    funding_inv = next((t for t in targets if t.get("target_id") == "btc_phase3_funding_skew_invert"), None)
    invert_note = None
    if funding and funding_inv:
        try:
            h0 = float(funding.get("hit_rate"))
            h1 = float(funding_inv.get("hit_rate"))
            invert_note = (
                f"funding hit={h0:.3f} invert={h1:.3f}; "
                + ("complementary (signal plausible)" if abs(h0 + h1 - 1.0) < 0.15 else "not complementary — review rule")
            )
        except (TypeError, ValueError):
            invert_note = "funding invert pair present; rates non-numeric"

    lines = [
        f"SANDBOX daily panel {panel.get('generated_at_utc', '')}: {len(targets)} targets, "
        f"{sum(1 for t in targets if t.get('ok'))} ok.",
    ]
    if top:
        lines.append(
            "Top: "
            + ", ".join(f"{t['target_id']}={t['hit_rate']:.1%}" if t.get("hit_rate") is not None else t["target_id"] for t in top[:3])
        )
    if invert_note:
        lines.append(f"Phase3 invert check: {invert_note}")
    lines.append("research_only — no prod score / live trading.")

    watchlist_block: list[dict[str, Any]] = []
    if rollup and isinstance(rollup.get("watchlist"), list):
        for w in rollup["watchlist"][:5]:
            watchlist_block.append(w)
        if watchlist_block:
            lines.append(
                "Watchlist (streak): "
                + ", ".join(
                    f"{w.get('target_id')} streak={w.get('streak_days')} 7d={w.get('mean_hit_last_7d')}"
                    for w in watchlist_block
                )
            )
    early_wl = (rollup or {}).get("early_watchlist") or []
    if early_wl and not watchlist_block:
        lines.append(
            "Early watchlist (2d): "
            + ", ".join(
                f"{w.get('target_id')} streak={w.get('streak_days')}"
                for w in early_wl[:5]
            )
        )

    promo_block: list[dict[str, Any]] = []
    if promotion and isinstance(promotion.get("candidates"), list):
        for c in promotion["candidates"][:5]:
            promo_block.append(c)
        if promo_block:
            lines.append(
                "Promotion research (not live): "
                + ", ".join(
                    f"{c.get('target_id')}={float(c.get('panel_hit_rate')):.1%}"
                    for c in promo_block
                )
            )

    bridge_line = None
    if bridge_draft:
        bridge_line = (
            f"Bridge draft: holdout={bridge_draft.get('n_tier_holdout_pass')} "
            f"early={bridge_draft.get('n_tier_early_watchlist')} "
            f"staging={bridge_draft.get('n_tier_panel_staging')} "
            f"— {bridge_draft.get('recommended_next_human_action')}"
        )
        lines.append(bridge_line)

    return {
        "schema": "sandbox_prophecy_brief_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "panel_ref": panel.get("stream_jsonl_ref"),
        "recent_trading_days": panel.get("recent_trading_days"),
        "n_targets": len(targets),
        "n_ok": sum(1 for t in targets if t.get("ok")),
        "leaderboard_top5": top,
        "leaderboard_bottom5": bottom,
        "phase3_funding_invert_check": invert_note,
        "rollup_ref": "reports/sandbox_prophecy_rollup_v1_latest.json" if rollup else None,
        "watchlist_candidates": watchlist_block,
        "n_watchlist_candidates": len(watchlist_block),
        "promotion_research_candidates": promo_block,
        "n_promotion_research_candidates": len(promo_block),
        "bridge_draft_ref": "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"
        if bridge_draft
        else None,
        "bridge_draft_summary": bridge_line,
        "brief_lines_ko": lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rollup-json", type=Path, default=DEFAULT_ROLLUP)
    ap.add_argument("--promotion-json", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--bridge-draft-json", type=Path, default=DEFAULT_BRIDGE_DRAFT)
    args = ap.parse_args()
    if not args.panel_json.is_file():
        print(f"Missing panel: {args.panel_json}", file=__import__("sys").stderr)
        return 2
    panel = json.loads(args.panel_json.read_text(encoding="utf-8-sig"))
    rollup = None
    if args.rollup_json.is_file():
        rollup = json.loads(args.rollup_json.read_text(encoding="utf-8-sig"))
    promotion = None
    if args.promotion_json.is_file():
        promotion = json.loads(args.promotion_json.read_text(encoding="utf-8-sig"))
    bridge_draft = None
    if args.bridge_draft_json.is_file():
        bridge_draft = json.loads(args.bridge_draft_json.read_text(encoding="utf-8-sig"))
    brief = build_brief(panel, rollup, promotion, bridge_draft)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in brief.get("brief_lines_ko") or []:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
