"""Consumer-safe daily guide title mapping."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "projects" / "no1kmedi" / "src" / "lib"))

# Mirror TS map via import path hack — read file contract instead
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryConsumerGuideLabelsV1.ts"


def test_consumer_guide_labels_module() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert "toConsumerGuideTitle" in text
    assert "오늘의 흐름" in text
    assert "마음 리듬" in text
    assert "return t;" in text
