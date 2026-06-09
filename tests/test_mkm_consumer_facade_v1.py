from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mkm_consumer_facade_v1 import (  # noqa: E402
    DISCLAIMER_DECK_KO,
    DISCLAIMER_MORNING_BEANS_KO,
    acode_from_sasang,
    deck_consumer_facade_block,
    enrich_deck_card_consumer,
    facade_morning_beans_card,
    morning_beans_consumer_headlines,
)

FORBIDDEN = ("Logos", "성경", "사주", "명리", "태양인", "태음인", "마법구슬")
DECK_SCRIPT = SCRIPTS / "build_mkmlife_news_observation_deck_v1.py"
EXPORT_SCRIPT = SCRIPTS / "export_mkm_morning_beans_mkmlife_card_v1.py"


def test_acode_from_sasang_maps_taeeum() -> None:
    row = acode_from_sasang("taeeum", deck_status="WATCH")
    assert row["consumer_archetype_id"].startswith("A-")
    assert row["consumer_display_name_ko"]
    assert "Logos" not in row["signal_channel_label_ko"]


def test_enrich_deck_card_consumer_fields() -> None:
    card = {"sasang_accent": "taeyang", "headline_ko": "sample"}
    enrich_deck_card_consumer(card, deck_status="WATCH")
    assert card.get("consumer_archetype_id")
    assert card.get("consumer_display_name_ko")


def test_facade_morning_beans_strips_theology() -> None:
    raw = {
        "lane": "logos_explain",
        "lens_slot": "logos",
        "title_ko": "Logos 맥락 · 성경 부록",
        "body_ko": "태양인(명리) 사주 기둥 참고",
    }
    out = facade_morning_beans_card(raw)
    combined = (out.get("consumer_title_ko") or "") + (out.get("consumer_body_ko") or "")
    for token in FORBIDDEN:
        assert token not in combined, token


def test_deck_disclaimers_no_theology() -> None:
    for text in (DISCLAIMER_DECK_KO, DISCLAIMER_MORNING_BEANS_KO):
        assert "Logos" not in text
        assert "성경" not in text


def test_deck_builder_emits_consumer_facade(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    news.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "observation_id": "00000000-0000-4000-8000-000000000042",
                "as_of_utc": "2026-05-10T08:00:00Z",
                "published_utc": "2026-05-10T08:00:00Z",
                "source_id": "external_feed_bbc_business",
                "canonical_text": "Finance headline sample",
                "text_sha256": "a347d2d11e94363755918d1b93704f1d9f2fba79ef8a32e874dda1d0b0491f35",
                "ingested_at_utc": "2026-05-10T08:01:00Z",
                "dataset_partition": "train_holdout",
                "hypothesis_tag": "[HYPO]",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    bench = tmp_path / "bench.json"
    bench.write_text(
        json.dumps({"metrics": {"jaccard_fidelity_proxy": 0.46, "token_saving_ratio": 0.39}}),
        encoding="utf-8",
    )
    pixel = tmp_path / "pixel.json"
    pixel.write_text(
        json.dumps(
            {
                "schema": "mkm_pixel_language_v1",
                "category_sprite_registry": {"finance": {"sprite_id": "PB_SPR_FINANCE_01"}},
                "category_sasang_default": {"finance": "taeeum"},
                "lens_media_mode_by_deck_status": {"WATCH": "defend", "HOLD": "idle"},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "deck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(DECK_SCRIPT),
            "--news-jsonl",
            str(news),
            "--bench-json",
            str(bench),
            "--phase1-json",
            str(tmp_path / "missing.json"),
            "--pixel-language-json",
            str(pixel),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("consumer_facade", {}).get("consumer_surface") == "a_code_wellness_archetype"
    assert doc.get("public_ui", {}).get("title")
    assert "Logos" not in (doc.get("disclaimer_ko") or "")
    card = doc["cards"][0]
    assert card.get("consumer_archetype_id")
    ui_blob = json.dumps(doc.get("public_ui") or {}, ensure_ascii=False)
    assert "Logos" not in ui_blob


def test_morning_beans_export_consumer_facade(tmp_path: Path) -> None:
    feed = {
        "schema": "mkm_morning_beans_feed_v1",
        "generated_at_utc": "2026-06-09T08:00:00Z",
        "feed_date_local": "2026-06-09",
        "field": {"regime_id": "covid", "regime_label_ko": "코로나"},
        "final": {"decision_label": "WATCH", "card_count": 2},
        "feed_policy": {"max_cards": 10, "anti_doomscroll": True, "session_ttl_minutes": 12},
        "cards": [
            {
                "card_id": "c1",
                "lane": "logos_explain",
                "lens_slot": "logos",
                "epistemic_label": "NON_GATING",
                "title_ko": "Logos 부록",
                "body_ko": "성경·사주 맥락",
                "deep_link": {"kind": "mkmlife_route", "path_or_route": "/oracle-sphere", "label_ko": "마법구슬 Logos"},
            },
            {
                "card_id": "c2",
                "lane": "personal_wellness",
                "lens_slot": "sasang",
                "epistemic_label": "HYPO",
                "title_ko": "태양인 아침",
                "body_ko": "태양인 루틴",
                "deep_link": {"kind": "none"},
            },
        ],
    }
    feed_path = tmp_path / "feed.json"
    feed_path.write_text(json.dumps(feed, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "card.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--feed-json",
            str(feed_path),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("consumer_facade")
    assert morning_beans_consumer_headlines()["headline_ko"] in (doc.get("headline_ko") or "")
    blob = json.dumps(
        {
            k: doc[k]
            for k in (
                "headline_ko",
                "subline_ko",
                "disclaimer_ko",
                "cards_display",
                "consumer_facade",
            )
        },
        ensure_ascii=False,
    )
    for token in ("Logos", "성경", "사주", "태양인", "마법구슬"):
        assert token not in blob, token
    assert deck_consumer_facade_block()["theology_verse_refs_stripped"] is True
