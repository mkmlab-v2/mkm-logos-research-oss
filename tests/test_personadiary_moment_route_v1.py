"""PersonaDiary moment assembler — meal intent on disk package when present."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assemble_personadiary_moment_response_v1 as asm  # noqa: E402

PKG = ROOT / "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"


def test_moment_on_latest_package_if_present() -> None:
    if not PKG.is_file():
        return
    package = json.loads(PKG.read_text(encoding="utf-8-sig"))
    doc = asm.assemble_moment_response(package, "오늘 점심 뭐 먹을까?")
    assert doc["intent"] == "meal"
    assert doc["schema"] == "personadiary_moment_response_v1"
    assert len(doc["cards"]) >= 1
    assert "AC-" in doc["summary_ko"] or "점심" in doc["summary_ko"]
