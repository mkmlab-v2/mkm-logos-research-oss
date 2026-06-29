"""FOUR_LENS_YINYANG_REGULARIZATION_V1.md — 5-slot structure smoke."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/research/FOUR_LENS_YINYANG_REGULARIZATION_V1.md"
REQUIRED_MARKERS = (
    "mkm_five_slot_lit_review_v1",
    "① 팩트 클레임",
    "④ 과장",
    "⑤ 벤치 매핑",
    "[Adoptable]",
    "[Needs experiment]",
    "merged_trade_direction",
    "geumhwa_index",
    "lens_pack@myeongni_timeline",
    "send_gate: HOLD",
)


def test_four_lens_yinyang_regularization_doc_present() -> None:
    assert DOC.is_file(), f"missing: {DOC}"
    text = DOC.read_text(encoding="utf-8-sig")
    for marker in REQUIRED_MARKERS:
        assert marker in text, f"missing marker: {marker}"
    assert text.count("| 1 |") >= 1
    assert text.count("| 10 |") >= 1
