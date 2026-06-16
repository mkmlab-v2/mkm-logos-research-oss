"""COORD anatomy overlay wire lib."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_parse_and_compact_coord_wire():
    from scripts.coord_anatomy_overlay_wire_v1_lib import (
        compact_coord_wire,
        parse_coord_wire_text,
    )

    doc = json.loads(
        (ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json").read_text(encoding="utf-8")
    )
    wire = doc["coord_wire_minimal"]
    parsed = parse_coord_wire_text(json.dumps(wire, ensure_ascii=False))
    assert parsed is not None
    compact = compact_coord_wire(wire)
    assert compact.startswith("[COORD:anatomy:v1:")


def test_materialize_coord_wire_renders_png(tmp_path: Path):
    from scripts.coord_anatomy_overlay_wire_v1_lib import materialize_coord_wire

    fixture = ROOT / "data/anatomy/fixtures/ninth_rib_lateral2.png"
    if not fixture.is_file():
        pytest.skip("ninth_rib fixture missing")
    doc = json.loads(
        (ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json").read_text(encoding="utf-8")
    )
    report = materialize_coord_wire(doc["coord_wire_minimal"], workspace_root=ROOT, out_dir=tmp_path)
    out = Path(report["output"])
    assert out.is_file()
    assert out.stat().st_size > 0
