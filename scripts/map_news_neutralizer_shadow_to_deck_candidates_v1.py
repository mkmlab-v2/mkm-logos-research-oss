#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map news_neutralizer_shadow_v1 → deck candidate cards (human promote only).

Default output: docs/final/artifacts/news_neutralizer_deck_candidates_v1_latest.json
Does NOT write mkmlife public/data unless --human-ack --copy-mkmlife-public (both required).

B-track [HYPO] · research_only · no Track A / live trading promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_mkmlife_news_observation_deck_v1 import (  # noqa: E402
    DEFAULT_PIXEL_LANGUAGE,
    _ASK_PREFILL_KO,
    _category_from_source_id,
    _content_lang,
    _headline_display_ko,
    _load_json,
    _load_pixel_language,
    _source_label_ko,
    _summary_display_ko,
    enrich_deck_card_consumer,
    map_category_to_pixel_meta,
)
from test_news_neutralizer_v1 import lint_shadow_doc_v1  # noqa: E402

DEFAULT_SHADOW = ROOT / "reports/news_neutralizer_shadow_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/news_neutralizer_deck_candidates_v1_latest.json"
DEFAULT_DECK_ARTIFACT = ROOT / "docs/final/artifacts/mkmlife_news_observation_deck_v1_latest.json"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/mkmlife_news_observation_deck_v1.json"

_FEED_ID_NORMALIZE: dict[str, str] = {
    "bbc_world": "bbc_world",
    "bbc_business": "bbc_business",
    "guardian_world": "guardian_world",
    "npr_news": "npr_news",
    "aljazeera_english": "aljazeera_english",
    "fixture": "fixture_feed",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _normalize_source_id(feed_id: str | None) -> str | None:
    if not feed_id:
        return None
    key = feed_id.strip().lower()
    return _FEED_ID_NORMALIZE.get(key, key)


def _observation_id(cluster_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"news-neutralizer:{cluster_id}"))


def _summary_from_bias(bias: dict[str, Any] | None, headline: str) -> str:
    if not bias:
        return _summary_display_ko(headline, headline)
    facts = [str(x) for x in (bias.get("shared_facts") or []) if str(x).strip()]
    if facts:
        body = " · ".join(facts[:2])
        if _content_lang(body) == "ko":
            return _summary_display_ko(body, headline if _content_lang(headline) == "en" else None)
        excerpt = body[:140]
        return f"편향 투명화 관측(B-track): {excerpt}… [HYPO]"
    note = str(bias.get("bias_transparency_note_ko") or "").strip()
    if note:
        return note[:280]
    return _summary_display_ko(headline, headline)


def build_candidates(
    shadow: dict[str, Any],
    *,
    max_cards: int,
    deck_status: str = "WATCH",
    pixel_lang: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    clusters = shadow.get("clusters") if isinstance(shadow.get("clusters"), list) else []
    analyses = shadow.get("bias_analyses") if isinstance(shadow.get("bias_analyses"), list) else []
    by_cluster: dict[str, dict[str, Any]] = {}
    for ba in analyses:
        if isinstance(ba, dict) and ba.get("cluster_id"):
            by_cluster[str(ba["cluster_id"])] = ba

    cards: list[dict[str, Any]] = []
    for cluster in clusters[:max_cards]:
        if not isinstance(cluster, dict):
            continue
        cluster_id = str(cluster.get("cluster_id") or "")
        headline = str(cluster.get("representative_headline") or "").strip()
        if not headline:
            continue
        bias = by_cluster.get(cluster_id)
        feed_ids = cluster.get("source_feed_ids") if isinstance(cluster.get("source_feed_ids"), list) else []
        source_id = _normalize_source_id(str(feed_ids[0]) if feed_ids else None)
        urls = cluster.get("source_urls") if isinstance(cluster.get("source_urls"), list) else []
        source_url = str(urls[0]) if urls else ""
        obs_id = _observation_id(cluster_id)
        display_ko, headline_original = _headline_display_ko(headline, source_id)
        category, category_label_ko = _category_from_source_id(source_id)
        card_id = hashlib.sha256(f"{cluster_id}:{headline}".encode("utf-8")).hexdigest()[:12]
        prefill = _ASK_PREFILL_KO

        overlay: dict[str, Any] = {
            "cluster_id": cluster_id,
            "member_count": cluster.get("member_count"),
            "bias_transparency_note_ko": (bias or {}).get("bias_transparency_note_ko"),
            "framing_signals": (bias or {}).get("framing_signals") or [],
            "shadow_generated_at_utc": shadow.get("generated_at_utc"),
            "provenance_mode": (shadow.get("provenance") or {}).get("mode"),
        }

        card: dict[str, Any] = {
            "card_id": card_id,
            "observation_id": obs_id,
            "headline_display_ko": display_ko,
            "headline_ko": display_ko,
            "compressed_summary": _summary_from_bias(bias, headline),
            "content_lang": _content_lang(headline),
            "source_label_ko": _source_label_ko(source_id),
            "as_of_utc": cluster.get("published_utc_max") or shadow.get("generated_at_utc"),
            "source_id": source_id,
            "source_record_url": source_url or None,
            "hypothesis_tag": "[HYPO]",
            "ask_one_prefill_ko": prefill,
            "oracle_sphere_href": f"/oracle-sphere?context={obs_id}",
            "ask_one_href": f"/ask-one?prefill={quote(prefill, safe='')}",
            "neutralizer_overlay": overlay,
            "promotion_status": "pending_human",
        }
        if headline_original:
            card["headline_original"] = headline_original
        if category:
            card["category"] = category
        if category_label_ko:
            card["category_label_ko"] = category_label_ko
        if pixel_lang:
            card.update(
                map_category_to_pixel_meta(
                    category,
                    deck_status=deck_status,
                    pixel_lang=pixel_lang,
                )
            )
            enrich_deck_card_consumer(card, deck_status=deck_status)
        cards.append(card)
    return cards


def build_candidates_doc(
    shadow: dict[str, Any],
    *,
    shadow_path: Path,
    max_cards: int,
    pixel_lang: dict[str, Any] | None,
) -> dict[str, Any]:
    synthesis = shadow.get("synthesis") if isinstance(shadow.get("synthesis"), dict) else {}
    cards = build_candidates(shadow, max_cards=max_cards, pixel_lang=pixel_lang)
    lint_source = {
        "synthesis": synthesis,
        "bias_analyses": shadow.get("bias_analyses") or [],
    }
    violations = lint_shadow_doc_v1(lint_source)
    return {
        "schema": "news_neutralizer_deck_candidates_v1",
        "generated_at_utc": _utc_now(),
        "lane": "research_only",
        "hypothesis_tag": "[HYPO]",
        "promotion_required": True,
        "promotion_status": "pending_human",
        "source_shadow": _rel(shadow_path),
        "synthesis_ref": {
            "topic_summary_ko": synthesis.get("topic_summary_ko"),
            "our_view_opinion_ko": synthesis.get("our_view_opinion_ko"),
            "disclaimer_ko": synthesis.get("disclaimer_ko"),
        },
        "candidate_cards": cards,
        "deck_merge_hint": {
            "max_cards": max_cards,
            "merge_policy": "prepend_pending_human_only",
            "public_copy_blocked_without_human_ack": True,
        },
        "copy_lint": {"passed": len(violations) == 0, "violations": violations},
    }


def _same_story_card(card: dict[str, Any], cand: dict[str, Any]) -> bool:
    url = str(cand.get("source_record_url") or "").strip()
    if url and str(card.get("source_record_url") or "").strip() == url:
        return True
    headline = str(cand.get("headline_original") or "").strip().casefold()
    if headline and str(card.get("headline_original") or "").strip().casefold() == headline:
        return True
    return False


def _apply_candidate_to_card(card: dict[str, Any], cand: dict[str, Any]) -> None:
    overlay = cand.get("neutralizer_overlay")
    if overlay:
        card["neutralizer_overlay"] = overlay
    for key in (
        "compressed_summary",
        "as_of_utc",
        "headline_original",
        "source_label_ko",
        "headline_display_ko",
        "headline_ko",
    ):
        if cand.get(key):
            card[key] = cand[key]
    card["hypothesis_tag"] = "[HYPO]"


def merge_into_deck_artifact(
    deck: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    max_merge: int,
) -> dict[str, Any]:
    merged = dict(deck)
    deck_cards = [dict(c) for c in (deck.get("cards") or []) if isinstance(c, dict)]
    existing_ids = {str(c.get("card_id")) for c in deck_cards if c.get("card_id")}
    to_add: list[dict[str, Any]] = []
    updates = 0
    for cand in candidates:
        if len(to_add) + updates >= max_merge:
            break
        cid = str(cand.get("card_id") or "")
        if not cid:
            continue
        story_idx = next((i for i, c in enumerate(deck_cards) if _same_story_card(c, cand)), None)
        if story_idx is not None:
            _apply_candidate_to_card(deck_cards[story_idx], cand)
            if story_idx > 0:
                deck_cards.insert(0, deck_cards.pop(story_idx))
            updates += 1
            continue
        if cid in existing_ids:
            overlay = cand.get("neutralizer_overlay")
            if overlay:
                for card in deck_cards:
                    if str(card.get("card_id")) == cid:
                        card["neutralizer_overlay"] = overlay
                        break
            continue
        row = {k: v for k, v in cand.items() if k != "promotion_status"}
        if "neutralizer_overlay" not in row:
            row.pop("neutralizer_overlay", None)
        row["hypothesis_tag"] = "[HYPO]"
        to_add.append(row)
    merged["cards"] = to_add + deck_cards
    merged["generated_at_utc"] = _utc_now()
    refs = merged.get("refs") if isinstance(merged.get("refs"), dict) else {}
    refs["neutralizer_candidates"] = "docs/final/artifacts/news_neutralizer_deck_candidates_v1_latest.json"
    merged["refs"] = refs
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description="shadow → deck candidate cards (human promote)")
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cards", type=int, default=5)
    ap.add_argument("--skip-pixel-meta", action="store_true")
    ap.add_argument("--strict-lint", action="store_true")
    ap.add_argument(
        "--merge-into-deck-artifact",
        type=Path,
        default=None,
        help="Merge pending candidates into deck artifact JSON (not public)",
    )
    ap.add_argument("--human-ack", action="store_true", help="Required for any public/merge write")
    ap.add_argument(
        "--copy-mkmlife-public",
        action="store_true",
        help="Also copy merged deck to mkmlife public/data (requires --human-ack)",
    )
    args = ap.parse_args()

    shadow_path = args.shadow_json.resolve()
    if not shadow_path.is_file():
        print(f"ERROR: missing shadow: {shadow_path}", file=sys.stderr)
        return 1
    shadow = json.loads(shadow_path.read_text(encoding="utf-8-sig"))
    if shadow.get("schema") != "news_neutralizer_shadow_v1":
        print(f"ERROR: unexpected schema: {shadow.get('schema')!r}", file=sys.stderr)
        return 1

    pixel_lang = None
    if not args.skip_pixel_meta and DEFAULT_PIXEL_LANGUAGE.is_file():
        try:
            pixel_lang = _load_pixel_language(DEFAULT_PIXEL_LANGUAGE)
        except ValueError as exc:
            print(f"WARN: pixel language skipped: {exc}", file=sys.stderr)

    doc = build_candidates_doc(
        shadow,
        shadow_path=shadow_path,
        max_cards=args.max_cards,
        pixel_lang=pixel_lang,
    )

    out_path = args.output_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": _rel(out_path), "cards": len(doc["candidate_cards"])}))

    if args.merge_into_deck_artifact or args.copy_mkmlife_public:
        if not args.human_ack:
            print("ERROR: --human-ack required for merge/public copy", file=sys.stderr)
            return 1
        deck_path = (args.merge_into_deck_artifact or DEFAULT_DECK_ARTIFACT).resolve()
        deck = _load_json(deck_path) if deck_path.is_file() else {}
        if deck and deck.get("schema") != "mkmlife_news_observation_deck_v1":
            print(f"ERROR: unexpected deck schema: {deck.get('schema')!r}", file=sys.stderr)
            return 1
        if not deck:
            deck = {
                "schema": "mkmlife_news_observation_deck_v1",
                "lane": "research_only",
                "hypothesis_tag": "[HYPO]",
                "deck_status": "WATCH",
                "cards": [],
            }
        merged = merge_into_deck_artifact(
            deck,
            doc["candidate_cards"],
            max_merge=args.max_cards,
        )
        deck_path.parent.mkdir(parents=True, exist_ok=True)
        deck_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"merged_deck_artifact": _rel(deck_path), "card_count": len(merged.get("cards") or [])}))
        if args.copy_mkmlife_public:
            MKMLIFE_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
            MKMLIFE_PUBLIC.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"mkmlife_public": _rel(MKMLIFE_PUBLIC)}))

    if args.strict_lint and not doc["copy_lint"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
