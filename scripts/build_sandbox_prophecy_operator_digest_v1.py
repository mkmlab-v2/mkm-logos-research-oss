#!/usr/bin/env python3
"""One-line operator digest for SANDBOX daily ops (thread log / handoff)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD = ROOT / "reports/sandbox_prophecy_ops_dashboard_v1_latest.json"
DEFAULT_HUMAN = ROOT / "reports/sandbox_prophecy_human_review_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_operator_digest_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else None


def build_digest(
    dashboard: dict[str, Any] | None,
    human: dict[str, Any] | None,
) -> dict[str, Any]:
    d = dashboard or {}
    top = (d.get("leaderboard_top3") or [])[:3]
    top_s = ", ".join(
        f"{t.get('target_id')}={float(t.get('hit_rate')):.1%}"
        for t in top
        if isinstance(t, dict) and t.get("hit_rate") is not None
    )
    milestone = (d.get("next_milestone_ko") or "").strip()
    line = (
        f"[SANDBOX] {d.get('n_targets', '?')}tgt "
        f"days={d.get('max_calendar_days')} "
        f"until_wl={d.get('days_until_watchlist_eligible')} "
        f"early={d.get('n_early_watchlist')} "
        f"holdout_pass={d.get('n_holdout_pass')} "
        f"top={top_s or 'n/a'} "
        f"research_only"
    )
    if milestone:
        line = f"{line} | next={milestone}"
    return {
        "schema": "sandbox_prophecy_operator_digest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "digest_line_ko": line,
        "human_review_status": (human or {}).get("status"),
        "recommended_next_human_action": d.get("recommended_next_human_action"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--print-line", action="store_true", default=True)
    args = ap.parse_args()

    doc = build_digest(_load(DEFAULT_DASHBOARD), _load(DEFAULT_HUMAN))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if args.print_line:
        print(doc["digest_line_ko"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
