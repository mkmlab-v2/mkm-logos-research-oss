from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_mkmlife_news_observation_deck_v1.py"


def test_build_mkmlife_news_observation_deck_smoke(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    rows = []
    for i in range(3):
        rows.append(
            {
                "schema_version": "news_observation_v1",
                "observation_id": f"00000000-0000-4000-8000-00000000000{i}",
                "as_of_utc": f"2026-05-{10 + i:02d}T08:00:00Z",
                "published_utc": f"2026-05-{10 + i:02d}T08:00:00Z",
                "source_id": "fixture_feed",
                "canonical_text": f"Headline {i} | detail {i}",
                "text_sha256": "a347d2d11e94363755918d1b93704f1d9f2fba79ef8a32e874dda1d0b0491f35",
                "ingested_at_utc": f"2026-05-{10 + i:02d}T08:01:00Z",
                "dataset_partition": "train_holdout",
                "hypothesis_tag": "[HYPO]",
            }
        )
    news.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    bench = tmp_path / "bench.json"
    bench.write_text(
        json.dumps(
            {
                "measurement_status": "COMPLETE",
                "metrics": {"token_saving_ratio": 0.39, "jaccard_fidelity_proxy": 0.46},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "deck.json"

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--bench-json",
            str(bench),
            "--phase1-json",
            str(tmp_path / "missing_phase1.json"),
            "--output-json",
            str(out),
            "--max-cards",
            "2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkmlife_news_observation_deck_v1"
    assert doc.get("deck_status") == "WATCH"
    assert len(doc.get("cards") or []) == 2
    top = doc["cards"][0]
    assert top.get("headline_original", "").startswith("Headline 2")
    assert "원문 영문" in (top.get("headline_display_ko") or top.get("headline_ko") or "")
    prefill = top.get("ask_one_prefill_ko") or ""
    assert "Headline" not in prefill
    assert "한 가지 질문" in prefill


def test_build_mkmlife_news_observation_deck_round_robin_two_categories(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    rows = []
    for i in range(4):
        rows.append(
            {
                "schema_version": "news_observation_v1",
                "observation_id": f"w0000000-0000-4000-8000-00000000000{i}",
                "as_of_utc": f"2026-05-2{i}T10:00:00Z",
                "published_utc": f"2026-05-2{i}T10:00:00Z",
                "source_id": "external_feed_bbc_world",
                "canonical_text": f"World {i}",
                "text_sha256": "a347d2d11e94363755918d1b93704f1d9f2fba79ef8a32e874dda1d0b0491f35",
                "ingested_at_utc": f"2026-05-2{i}T10:01:00Z",
                "dataset_partition": "train_holdout",
                "hypothesis_tag": "[HYPO]",
            }
        )
    for i in range(4):
        rows.append(
            {
                "schema_version": "news_observation_v1",
                "observation_id": f"f0000000-0000-4000-8000-00000000000{i}",
                "as_of_utc": f"2026-05-2{i}T11:00:00Z",
                "published_utc": f"2026-05-2{i}T11:00:00Z",
                "source_id": "external_feed_bbc_business",
                "canonical_text": f"Finance {i}",
                "text_sha256": "a347d2d11e94363755918d1b93704f1d9f2fba79ef8a32e874dda1d0b0491f35",
                "ingested_at_utc": f"2026-05-2{i}T11:01:00Z",
                "dataset_partition": "train_holdout",
                "hypothesis_tag": "[HYPO]",
            }
        )
    news.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    bench = tmp_path / "bench.json"
    bench.write_text(
        json.dumps({"metrics": {"jaccard_fidelity_proxy": 0.46, "token_saving_ratio": 0.39}}),
        encoding="utf-8",
    )
    out = tmp_path / "deck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--bench-json",
            str(bench),
            "--phase1-json",
            str(tmp_path / "missing.json"),
            "--output-json",
            str(out),
            "--max-cards",
            "5",
            "--deck-selection",
            "round_robin",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["deck_selection"]["mode"] == "round_robin_by_category"
    assert len(doc["cards"]) == 5
    labels = {c.get("category_label_ko") for c in doc["cards"]}
    assert "세계" in labels and "경제" in labels


def test_build_mkmlife_news_observation_deck_category_badge(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    news.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "observation_id": "00000000-0000-4000-8000-000000000042",
                "as_of_utc": "2026-05-10T08:00:00Z",
                "published_utc": "2026-05-10T08:00:00Z",
                "source_id": "external_feed_bbc_world",
                "canonical_text": "World headline sample",
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
    out = tmp_path / "deck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--bench-json",
            str(bench),
            "--phase1-json",
            str(tmp_path / "missing.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    card = json.loads(out.read_text(encoding="utf-8"))["cards"][0]
    assert card.get("category") == "world"
    assert card.get("category_label_ko") == "세계"


def test_build_mkmlife_news_observation_deck_pixel_meta(tmp_path: Path) -> None:
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
                "category_sprite_registry": {
                    "finance": {"sprite_id": "PB_SPR_FINANCE_01"},
                    "other": {"sprite_id": "PB_SPR_OBS_01"},
                },
                "category_sasang_default": {"finance": "taeeum", "other": "taeeum"},
                "lens_media_mode_by_deck_status": {"WATCH": "defend", "HOLD": "idle"},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "deck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
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
    assert doc.get("pixel_meta_schema_version") == "1"
    card = doc["cards"][0]
    assert card.get("pixel_sprite_id") == "PB_SPR_FINANCE_01"
    assert card.get("sasang_accent") == "taeeum"
    assert card.get("lens_media_key") == "LM_HP050_TAEEUM_DEFEND_V1"


def test_build_mkmlife_news_observation_deck_korean_headline_no_original(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    news.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "observation_id": "00000000-0000-4000-8000-000000000099",
                "as_of_utc": "2026-05-10T08:00:00Z",
                "published_utc": "2026-05-10T08:00:00Z",
                "source_id": "fixture_feed",
                "canonical_text": "한국어 헤드라인 샘플 | 본문",
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
    out = tmp_path / "deck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--bench-json",
            str(bench),
            "--phase1-json",
            str(tmp_path / "missing.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    card = json.loads(out.read_text(encoding="utf-8"))["cards"][0]
    assert card.get("headline_display_ko", "").startswith("한국어")
    assert "headline_original" not in card
    assert card.get("content_lang") == "ko"


def test_build_mkmlife_news_observation_deck_hold_on_low_jaccard(tmp_path: Path) -> None:
    news = tmp_path / "news.jsonl"
    news.write_text(
        json.dumps(
            {
                "schema_version": "news_observation_v1",
                "observation_id": "00000000-0000-4000-8000-000000000001",
                "as_of_utc": "2026-05-10T08:00:00Z",
                "published_utc": "2026-05-10T08:00:00Z",
                "source_id": "fixture_feed",
                "canonical_text": "Sample headline",
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
        json.dumps({"metrics": {"jaccard_fidelity_proxy": 0.30, "token_saving_ratio": 0.20}}),
        encoding="utf-8",
    )
    out = tmp_path / "deck.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--news-jsonl",
            str(news),
            "--bench-json",
            str(bench),
            "--phase1-json",
            str(tmp_path / "missing.json"),
            "--output-json",
            str(out),
            "--jaccard-floor",
            "0.40",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("deck_status") == "HOLD"
    assert doc.get("hold_reason")
