#!/usr/bin/env python3
"""Export MKM Morning Beans feed as mkmlife deck card (research_only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mkm_consumer_facade_v1 import (  # noqa: E402
    DISCLAIMER_MORNING_BEANS_KO,
    facade_morning_beans_card,
    morning_beans_consumer_headlines,
)
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_FEED = ART / "mkm_morning_beans_feed_v1_latest.json"
DEFAULT_OUT = ART / "mkm_morning_beans_mkmlife_card_v1_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects" / "mkm" / "mkm-life" / "public" / "data"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def build_card(feed: dict[str, Any]) -> dict[str, Any]:
    field = feed.get("field") or {}
    final = feed.get("final") or {}
    policy = feed.get("feed_policy") or {}
    cards = feed.get("cards") or []

    cards_display = []
    for c in cards:
        dl = c.get("deep_link") or {}
        raw = {
                "card_id": c.get("card_id"),
                "lane": c.get("lane"),
                "epistemic_label": c.get("epistemic_label"),
                "lens_slot": c.get("lens_slot"),
                "title_ko": c.get("title_ko"),
                "body_ko": c.get("body_ko"),
                "deep_link_kind": dl.get("kind", "none"),
                "deep_link": dl.get("path_or_route"),
                "deep_link_label_ko": dl.get("label_ko"),
            }
        cards_display.append(facade_morning_beans_card(raw))

    consumer_head = morning_beans_consumer_headlines()

    return {
        "schema": "mkm_morning_beans_mkmlife_card_v1",
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": feed.get("generated_at_utc") or _utc_now(),
        "feed_date_local": feed.get("feed_date_local"),
        "regime_id": field.get("regime_id"),
        "regime_label_ko": field.get("regime_label_ko"),
        "decision_label": final.get("decision_label", "WATCH"),
        "final_action": (feed.get("pipeline_summary") or {}).get("final_action"),
        "card_count": final.get("card_count", len(cards)),
        "max_cards_policy": policy.get("max_cards", 10),
        "anti_doomscroll": policy.get("anti_doomscroll", True),
        "session_ttl_minutes": policy.get("session_ttl_minutes", 12),
        "headline_ko": consumer_head["headline_ko"],
        "subline_ko": consumer_head["subline_ko"],
        "disclaimer_ko": DISCLAIMER_MORNING_BEANS_KO,
        "consumer_facade": {
            "schema": "saving_the_news_public_copy_facade_v1",
            "version": "1.0.0",
            "theology_verse_refs_stripped": True,
            "consumer_surface": "a_code_wellness_archetype",
        },
        "cards_display": cards_display,
        "pipeline_summary_ko": (feed.get("pipeline_summary") or {}).get("conflict_note_ko"),
        "refs": {
            "feed": _rel(DEFAULT_FEED),
            "commander_profile": (feed.get("subject_ref") or {}).get("profile_path"),
            "macro_briefing": "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json",
        },
        "forbidden": [
            "Not Track A or live trading trigger.",
            "Not Gmail-scale cross-app personalization.",
            "Context appendix cards are NON_GATING only.",
            "Not consumer app launch proof.",
        ],
        "audit": {
            "guardrail_script_exit": (feed.get("audit") or {}).get("guardrail_script_exit", 0),
            "model_route": (feed.get("audit") or {}).get("model_route", "local_stub_no_llm"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feed-json", type=Path, default=DEFAULT_FEED)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--copy-mkmlife-public", action="store_true")
    args = ap.parse_args()

    feed = _read(args.feed_json.resolve())
    if not feed or feed.get("schema") != "mkm_morning_beans_feed_v1":
        raise SystemExit(f"missing or invalid feed: {args.feed_json}")

    card = build_card(feed)
    out = args.output_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": _rel(out),
                "card_count": card["card_count"],
                "regime_id": card["regime_id"],
            },
            ensure_ascii=False,
        )
    )

    if args.copy_mkmlife_public:
        MKMLIFE_PUBLIC.mkdir(parents=True, exist_ok=True)
        dest = MKMLIFE_PUBLIC / "mkm_morning_beans_card_v1.json"
        dest.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {_rel(dest)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
