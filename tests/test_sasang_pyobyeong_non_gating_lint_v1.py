"""Static non-gating lint — pyobyeong cards + interpretive bundle (P1-2)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PROMOTION_PAT = re.compile(
    r"promotion_to_a_track_allowed\s*[=:]\s*true|send_gate\s*[=:]\s*[\"']?send\b|start_live_trading",
    re.I,
)
REQUIRED_HOLD_PAT = re.compile(r"send_gate|HOLD|human_only|Track A|CDSS|처방", re.I)

EXP = ROOT / "experiments" / "sasang-head-btrack"


def _first_existing(*paths: Path) -> Path:
    for p in paths:
        if p.is_file():
            return p
    raise AssertionError(f"missing all: {[str(p) for p in paths]}")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cards_path() -> Path:
    return _first_existing(
        ROOT / "docs/final/artifacts/sasang_pyobyeong_insight_cards_v1_latest.json",
        EXP / "artifacts/ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json",
        EXP / "artifacts/ijeoma_pyobyeong_insight_cards_v1_latest.json",
    )


def _lit_review_path() -> Path:
    return _first_existing(
        ROOT / "docs/research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md",
        EXP / "research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md",
    )


def test_pyobyeong_cards_non_gating_contract():
    path = _cards_path()
    doc = _load_json(path)
    assert doc.get("research_only") is True
    assert doc.get("send_gate") == "HOLD"
    if "track_a_promotion_allowed" in doc:
        assert doc["track_a_promotion_allowed"] is False
    else:
        for cand in (
            ROOT / "docs/final/artifacts/sasang_pyobyeong_promotion_paper_verdict_v1_latest.json",
            EXP / "artifacts/sasang_pyobyeong_promotion_paper_verdict_v1.json",
        ):
            if cand.is_file():
                promo = (_load_json(cand).get("slots") or {}).get("promotion") or {}
                assert promo.get("track_a_promotion_allowed") is False
                break
    blob = path.read_text(encoding="utf-8")
    assert not FORBIDDEN_PROMOTION_PAT.search(blob)
    assert REQUIRED_HOLD_PAT.search(blob)
    for card in doc.get("cards") or []:
        assert card.get("send_gate", "HOLD") == "HOLD"


def test_interpretive_bundle_no_clinical_auto_trigger():
    path = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
    if not path.is_file():
        pytest.skip("interpretive bundle only on workspace main after promote")
    doc = _load_json(path)
    assert doc.get("rail") == "B_TRACK"
    assert doc.get("decision_authority") == "human_only"
    blob = path.read_text(encoding="utf-8")
    assert not FORBIDDEN_PROMOTION_PAT.search(blob)
    byeong = next((s for s in doc.get("sections") or [] if s.get("axis_id") == "byeongjeung_yakri"), None)
    assert byeong is not None
    sw = byeong.get("symptom_weights_v1") or {}
    assert sw.get("auto_clinical_trigger") is False


def test_lit_review_advisory_only_markers():
    path = _lit_review_path()
    blob = path.read_text(encoding="utf-8")
    assert not FORBIDDEN_PROMOTION_PAT.search(blob)
    assert "human_only" in blob or "advisory_only" in blob
    assert "CDSS" in blob or "Track A" in blob
