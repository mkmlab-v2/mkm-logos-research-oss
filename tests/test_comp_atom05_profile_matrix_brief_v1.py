"""comp_atom05 profile matrix brief — operator guide fields."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_brief_v1.json"


def test_profile_matrix_brief_has_operator_guide() -> None:
    assert BRIEF.is_file(), "run: py scripts/comp_atom05_profile_matrix_brief_v1.py"
    doc = json.loads(BRIEF.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
    guide = doc.get("operator_guide_ko") or {}
    assert guide.get("title")
    cells = guide.get("cells_full_v2_40") or []
    assert len(cells) == 4
    presets = doc.get("profile_presets") or {}
    assert presets["track_a_frozen"]["graph_wire_selective_bridge"] is False
    assert presets["btrack_recommended_v2"]["graph_wire_selective_bridge"] is True
    pitfalls = guide.get("pitfalls") or []
    assert any("47.1" in p or "단일" in p for p in pitfalls)
