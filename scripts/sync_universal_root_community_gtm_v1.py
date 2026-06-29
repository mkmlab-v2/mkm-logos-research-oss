#!/usr/bin/env python3
"""Patch universal_root_community_gtm_v1_latest.json from commander/agent flags."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/universal_root_community_gtm_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--x-posts-2-4-posted", action="store_true")
    ap.add_argument("--x-correction-replied", action="store_true")
    ap.add_argument("--reddit-correction-commented", action="store_true")
    ap.add_argument("--reddit-deferred", action="store_true", help="Commander skip Reddit channel (filter removed)")
    ap.add_argument("--ur-w3-complete", action="store_true", help="contributor example already on main")
    ap.add_argument("--external-repro-count", type=int, default=None)
    args = ap.parse_args()

    if not OUT.is_file():
        print(json.dumps({"ok": False, "error": "gtm_json_missing"}))
        return 1

    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    doc["updated_at_utc"] = _utc()

    if args.x_posts_2_4_posted:
        x = doc.setdefault("channels", {}).setdefault("x", {})
        x["status"] = "posted_1_4"
        x["posts_published_min"] = 4
        x["posts_ready"] = []
        x["posted_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        x["posted_by"] = "commander"
        x.setdefault(
            "post_urls",
            {},
        )
        x["post_urls"].setdefault(
            "2",
            "https://x.com/moksorinw/status/2068734802661175789",
        )
        milestones = doc.setdefault("milestones", {})
        ur_w1 = milestones.setdefault("UR-W1", {})
        ur_w1["status"] = "partial_complete"
        ur_w1["note"] = "Reddit + X 1-4 posted 2026-06-21; Discussions external repro ≥1 still pending"
        next_actions = doc.get("next_actions") or []
        doc["next_actions"] = [a for a in next_actions if "X posts 2-4" not in a]

    if args.x_correction_replied:
        x = doc.setdefault("channels", {}).setdefault("x", {})
        x["status"] = "correction_replied"
        x["correction_replied_at_utc"] = _utc()
        x["correction_reply_to"] = "https://x.com/moksorinw/status/2068734802661175789"
        next_actions = doc.get("next_actions") or []
        doc["next_actions"] = [
            a
            for a in next_actions
            if "X correction" not in a
            and "correction reply" not in a.lower()
            and "reply on X" not in a
        ]

    if args.reddit_correction_commented:
        rd = doc.setdefault("channels", {}).setdefault("reddit_local_llm", {})
        rd["status"] = "correction_commented"
        rd["correction_commented_at_utc"] = _utc()
        next_actions = doc.get("next_actions") or []
        doc["next_actions"] = [
            a for a in next_actions if "Reddit correction" not in a and "reddit correction" not in a.lower()
        ]

    if args.reddit_deferred:
        rd = doc.setdefault("channels", {}).setdefault("reddit_local_llm", {})
        rd["status"] = "deferred"
        rd["deferred_at_utc"] = _utc()
        rd["deferred_by"] = "commander"
        rd["deferred_reason"] = "filter_removed_skip_channel"
        rd["correction_required"] = False
        next_actions = doc.get("next_actions") or []
        doc["next_actions"] = [a for a in next_actions if "reddit" not in a.lower() and "Reddit" not in a]

    if args.ur_w3_complete:
        milestones = doc.setdefault("milestones", {})
        milestones["UR-W3"] = {
            "status": "complete",
            "note": "contributor_example_v1.json on main; validate+bench+pytest exit 0",
            "evidence": milestones.get("UR-W3", {}).get("evidence"),
        }
        next_actions = doc.get("next_actions") or []
        doc["next_actions"] = [
            a for a in next_actions if "contributor PR" not in a and "UR-W3" not in a
        ]

    if args.external_repro_count is not None:
        gh = doc.setdefault("channels", {}).setdefault("github_discussions", {})
        gh["external_repro_reports"] = args.external_repro_count
        if args.external_repro_count >= 1:
            doc.setdefault("milestones", {})["UR-W1"] = {
                "status": "complete",
                "note": f"external repro reports={args.external_repro_count}",
            }

    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
