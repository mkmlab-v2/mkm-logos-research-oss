#!/usr/bin/env python3
"""Post-run summary for marketing weekly bundle (cost tier + queue + draft paths)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TIER = ROOT / "docs/final/artifacts/marketing_ops_cost_tier_v1_latest.json"
UNIFIED = ROOT / "data/marketing/marketing_content_queue.json"
DRAFTS = ROOT / "reports/marketing/linkedin_drafts"
DEFAULT_OUT = ROOT / "reports/marketing/marketing_weekly_bundle_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(*, gemini_used: bool) -> dict[str, Any]:
    tier = _load(TIER) or {}
    unified = _load(UNIFIED)
    active_tier = (unified or {}).get("active_cost_tier") or (unified or {}).get("default_cost_tier") or "tier_0"
    event_week = (unified or {}).get("tier15_event_week") or {}
    by_channel: dict[str, int] = {}
    pending_non_linkedin: list[str] = []
    if unified:
        for item in unified.get("items", []):
            ch = str(item.get("channel", "unknown"))
            by_channel[ch] = by_channel.get(ch, 0) + 1
            if ch != "linkedin" and item.get("status") == "pending":
                pending_non_linkedin.append(f"{item.get('id')}:{ch}")

    drafts = []
    if DRAFTS.is_dir():
        drafts = sorted(p.name for p in DRAFTS.iterdir() if p.name.endswith("_[DRAFT].md"))

    recommended = active_tier if unified else tier.get("recommended_default", "tier_0")
    if gemini_used and recommended == "tier_0":
        recommended = "tier_15"

    return {
        "schema": "marketing_weekly_bundle_summary_v1",
        "generated_at_utc": _utc_now(),
        "cost_tier_pointer": TIER.relative_to(ROOT).as_posix(),
        "active_cost_tier": active_tier,
        "tier15_event_week_enabled": bool(event_week.get("enabled")),
        "recommended_cost_tier": recommended,
        "gemini_used_this_run": gemini_used,
        "queue_counts_by_channel": by_channel,
        "pending_non_linkedin_generators": pending_non_linkedin,
        "linkedin_draft_files": drafts[:20],
        "linkedin_draft_count": len(drafts),
        "human_publish_only": True,
        "boundary_ack": "Drafts are [DRAFT]; no API publish. B-track [HYPO] not auto-promoted.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--gemini-used", action="store_true")
    args = ap.parse_args()
    doc = build(gemini_used=args.gemini_used)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
