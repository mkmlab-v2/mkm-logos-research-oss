"""Smoke: score_aramaic_regime_shift_v1 CLI writes JSON matching aramaic_regime_shift_score_v1 schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "score_aramaic_regime_shift_v1.py"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "aramaic_regime_shift_score_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def _sample_edge() -> dict:
    return {
        "schema": "aramaic_graph_edge_v1",
        "src_node_id": "aramaic::Dan.2.4",
        "dst_node_id": "aramaic::Dan.2.5",
        "edge_type": "timeline_anchor",
        "weight": 0.72,
        "confidence": 0.78,
        "evidence": "stub",
        "as_of_utc": "2020-01-01T00:00:00Z",
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "semantic_overlap": 0.35,
        "shared_token_count": 2,
        "relation_basis": ["token_overlap"],
    }


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_score_aramaic_regime_shift_cli_smoke(tmp_path: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "score.json"
    edges.write_text(json.dumps(_sample_edge(), ensure_ascii=False) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--edges-jsonl",
            str(edges),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc.get("schema") == "aramaic_regime_shift_score_v1"
    assert doc.get("insight_signal_applied") is False


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_score_aramaic_regime_shift_with_insight_flag(tmp_path: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    edges = tmp_path / "edges.jsonl"
    out = tmp_path / "score.json"
    edges.write_text(json.dumps(_sample_edge(), ensure_ascii=False) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--edges-jsonl",
            str(edges),
            "--include-insight-signal",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc.get("insight_signal_applied") is True
