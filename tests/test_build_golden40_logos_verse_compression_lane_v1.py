"""Logos verse lane harvest smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_golden40_logos_verse_compression_lane_v1 import _harvest, _verse_raw


def test_verse_raw_min_length() -> None:
    raw = _verse_raw(
        {
            "source_ref": "Gen 1:1",
            "edition": "BHS",
            "text": "ב/ראשית ברא אלהים",
            "interpretation": "게마트리아 값",
        }
    )
    assert len(raw) >= 20


def test_harvest_stride(tmp_path: Path) -> None:
    jl = tmp_path / "v.jsonl"
    rows = [
        {"verse_id": f"G.{i}", "source_ref": f"G {i}", "edition": "BHS", "text": "x" * 30}
        for i in range(10)
    ]
    jl.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    cases = _harvest(jl, max_cases=3, min_chars=20, stride=2)
    assert len(cases) == 3
    assert cases[0]["id"] == "logos_v_0001"
