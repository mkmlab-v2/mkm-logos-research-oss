"""infer_media_segment_provenance_v0 — auto-tag rules."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.infer_media_segment_provenance_v0 import (
    enrich_segments_provenance_v0,
    infer_provenance_hint_v0,
)


def test_infer_debunked_fake_for_sitchin_nibiru() -> None:
    neg = ["시친", "니비루", "아누나키", "외계인"]
    text = "아누나키는 외계인이고 니비루에서 왔다며 시친이 주장했습니다."
    assert infer_provenance_hint_v0(text, negative_keywords=neg) == "debunked_fake"


def test_infer_scholarly_fact_for_exile_message() -> None:
    pos = ["바빌론", "유수", "종교학", "학자", "메시지"]
    text = "종교학자들은 내용은 같아 보여도 전하는 메시지는 엄연히 다르다고 말합니다."
    assert infer_provenance_hint_v0(text, theme_keywords=pos) == "scholarly_fact"


def test_infer_multilens_for_serpent() -> None:
    text = "오피스 신앙에서 뱀은 무지에서 인간을 해방시키는 존재로 여겨졌습니다."
    assert infer_provenance_hint_v0(text) == "multilens_hypo"


def test_enrich_polluted_fixture_auto_tags() -> None:
    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests/fixtures/media_stt_transcription_polluted_bench_v1.json"
    )
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    enriched = enrich_segments_provenance_v0(
        doc["segments"],
        theme_keywords=doc["theme_keywords"],
        negative_keywords=doc.get("negative_keywords"),
    )
    by_id = {s["id"]: s["provenance_hint"] for s in enriched}
    assert by_id["seg_04"] == "scholarly_fact"
    assert by_id["seg_14"] == "debunked_fake"
    assert by_id["seg_15"] == "debunked_fake"
    assert by_id["seg_16"] == "debunked_fake"
    assert by_id["seg_18"] == "debunked_fake"
    assert by_id["seg_06"] == "multilens_hypo"
    assert by_id["seg_12"] in {"mixed", "debunked_fake"}
