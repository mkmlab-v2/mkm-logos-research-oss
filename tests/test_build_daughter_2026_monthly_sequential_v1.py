"""Smoke tests for build_daughter_2026_monthly_sequential_v1.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_daughter_2026_monthly_sequential_v1.py"
SCHEMA = ROOT / "docs/final/schemas/daughter_2026_monthly_sequential_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_daughter_monthly_sequential_cli(tmp_path: Path) -> None:
    out_json = tmp_path / "monthly.json"
    md_out = tmp_path / "monthly.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out-json",
            str(out_json),
            "--md-out",
            str(md_out),
            "--strict-schema",
        ],
        cwd=ROOT,
        check=True,
    )
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)

    assert doc["schema"] == "daughter_2026_monthly_sequential_v1"
    assert doc["fusion_mode"] == "sequential_blocks_not_monthly_parallel_merge"
    assert doc["rag_graph_runtime"] is False
    assert len(doc["months"]) == 12

    layer_ids = [layer["layer_id"] for layer in doc["months"][0]["layers"]]
    assert layer_ids == ["core", "myeongni", "sasang", "logos"]

    jan = doc["months"][0]
    assert jan["peak_flags"]["wealth_peak"] is True
    logos = next(l for l in jan["layers"] if l["layer_id"] == "logos")
    assert logos["junction_trigger_id"] == "comparison_heart"

    assert md_out.is_file()
    md = md_out.read_text(encoding="utf-8")
    assert "12월" in md
    assert "GraphRAG" in md or "합선" in md
