#!/usr/bin/env python3
"""Saving the News design UI surfaces status (mkmlife + jemaai, research_only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
MKMLIFE_PUBLIC = ROOT / "projects" / "mkm" / "mkm-life" / "public" / "data"
OUT_JSON = ART / "saving_the_news_design_ui_status_v1_latest.json"

DECK_ART = ART / "mkmlife_news_observation_deck_v1_latest.json"
HP_CARD_ART = ART / "hyper_personal_news_intake_mkmlife_card_v1_latest.json"
PANEL_ART = ART / "saving_the_news_matrix_panel_slice_v1_latest.json"
TOPO_ART = ART / "saving_the_news_showroom_topology_slice_v1_latest.json"

DECK_PUBLIC = MKMLIFE_PUBLIC / "mkmlife_news_observation_deck_v1.json"
HP_PUBLIC = MKMLIFE_PUBLIC / "hyper_personal_news_intake_card_v1.json"
NEWS_DECK_TSX = ROOT / "projects/mkm/mkm-life/components/news-deck/NewsObservationDeck.tsx"
HP_BADGE_TSX = ROOT / "projects/mkm/mkm-life/components/magic-orb/HyperPersonalPriorBadge.tsx"
MATRIX_HTML = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_saving_the_news_matrix_v1.html"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_status() -> dict[str, Any]:
    deck = _read(DECK_ART)
    hp = _read(HP_CARD_ART)
    panel = _read(PANEL_ART)
    topo = _read(TOPO_ART)
    lane = topo.get("mkmlife_consumer_lane") or panel.get("mkmlife_consumer_lane") or {}
    footnote = panel.get("compression_dual_footnote") or {}
    cards = deck.get("cards") or []
    hp_linked_cards = sum(1 for c in cards if isinstance(c, dict) and c.get("hp_shadow_linked"))

    exit_criteria = {
        "D1_mkmlife_deck_artifact": DECK_ART.is_file() and deck.get("schema") == "mkmlife_news_observation_deck_v1",
        "D2_mkmlife_deck_public": DECK_PUBLIC.is_file(),
        "D3_hp_card_artifact": HP_CARD_ART.is_file() and hp.get("schema") == "hyper_personal_news_intake_mkmlife_card_v1",
        "D4_hp_card_public": HP_PUBLIC.is_file(),
        "D5_deck_card_count_6_9_target": 6 <= len(cards) <= 9,
        "D6_hp_shadow_on_cards": hp_linked_cards >= min(len(cards), 1) if cards else False,
        "D7_news_deck_component": NEWS_DECK_TSX.is_file(),
        "D8_oracle_sphere_hp_badge": HP_BADGE_TSX.is_file(),
        "D9_jemaai_matrix_hp_footnote": bool(footnote.get("raw") and footnote.get("operational_post_processor")),
        "D10_jemaai_matrix_html": MATRIX_HTML.is_file(),
        "D11_topology_mkmlife_lane": bool(lane.get("card_count")),
        "shadow_observation_only": True,
        "cms_publish_allowed": False,
    }
    guard_flags = {
        "shadow_observation_only": True,
        "cms_publish_allowed": False,
    }
    positive = {k: v for k, v in exit_criteria.items() if k not in guard_flags}
    complete = all(positive.values()) and all(
        exit_criteria.get(k) == expected for k, expected in guard_flags.items()
    )

    return {
        "schema": "saving_the_news_design_ui_status_v1",
        "phase": "Design UI — mkmlife deck + oracle-sphere §10 + jemaai footnote [HYPO]",
        "status": "DESIGN_UI_POC_COMPLETE" if complete else "DESIGN_UI_IN_PROGRESS",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "exit_criteria": exit_criteria,
        "surfaces": {
            "mkmlife_news_deck": {
                "url": "https://mkmlife.com/news-deck",
                "card_count": len(cards),
                "deck_max_cards": (deck.get("deck_selection") or {}).get("max_cards"),
                "deck_status": deck.get("deck_status"),
                "hp_linked_card_count": hp_linked_cards,
            },
            "mkmlife_oracle_sphere": {
                "url": "https://mkmlife.com/oracle-sphere",
                "hp_badge_component": "HyperPersonalPriorBadge.tsx",
            },
            "jemaai_matrix": {
                "html": str(MATRIX_HTML.relative_to(ROOT)).replace("\\", "/"),
                "compression_dual_footnote": bool(footnote),
                "mkmlife_consumer_lane_card_count": lane.get("card_count"),
            },
        },
        "explicit_gaps": [
            "mkmlife asset deploy via Run-MkmlifeNewsObservationFusionChain -DeployMkmlifeAssets; /news-deck route may need -FullMkmlifeDeploy once.",
            "Live breaking-news stream UI not shipped.",
            "DSPy/GEPA product UI not implemented.",
            "CMS publish lock product not shipped.",
        ],
        "refs": {
            "deck_artifact": "docs/final/artifacts/mkmlife_news_observation_deck_v1_latest.json",
            "hp_card_artifact": "docs/final/artifacts/hyper_personal_news_intake_mkmlife_card_v1_latest.json",
            "panel_slice": "docs/final/artifacts/saving_the_news_matrix_panel_slice_v1_latest.json",
            "blueprint": "docs/research/saving_the_news_blueprint_v1.md",
        },
    }


def main() -> int:
    doc = build_status()
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON} status={doc['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
