# -*- coding: utf-8 -*-
"""JSON Schema validation for Yang(2015) B-track metrics + celebrity benchmark output."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_BTRACK = _ROOT / "docs" / "final" / "schemas" / "btrack_yang_2015_style_metrics_v1.schema.json"
_SCHEMA_HIT = _ROOT / "docs" / "final" / "schemas" / "myeongni_celebrity_hit_rate_v1.schema.json"
_SCRIPT_BTRACK = _ROOT / "scripts" / "btrack_yang_2015_style_metrics_v1.py"
_SCRIPT_BENCH = _ROOT / "scripts" / "run_myeongni_celebrity_benchmark_v1.py"
_DATASET = _ROOT / "data" / "myeongni" / "celebrity_saju_benchmark_v1.jsonl"


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schemas_parse():
    assert _SCHEMA_BTRACK.is_file()
    assert _SCHEMA_HIT.is_file()
    assert _load_schema(_SCHEMA_BTRACK)["properties"]["schema"]["const"] == "btrack_yang_2015_style_metrics_v1"
    assert _load_schema(_SCHEMA_HIT)["properties"]["schema"]["const"] == "myeongni_celebrity_hit_rate_v1"


def test_btrack_cli_output_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema(_SCHEMA_BTRACK)
    commander = {
        "advanced": {
            "input_summary": {
                "pillars": {
                    "year": "갑자",
                    "month": "갑자",
                    "day": "경진",
                    "hour": "갑자",
                }
            }
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fin:
        json.dump(commander, fin, ensure_ascii=False)
        in_path = Path(fin.name)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        p = subprocess.run(
            [sys.executable, str(_SCRIPT_BTRACK), "--input", str(in_path), "--out", str(out)],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert p.returncode == 0, p.stderr + p.stdout
        doc = json.loads(out.read_text(encoding="utf-8"))
        jsonschema.validate(instance=doc, schema=schema)
    finally:
        in_path.unlink(missing_ok=True)
        out.unlink(missing_ok=True)


def test_celebrity_benchmark_output_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema(_SCHEMA_HIT)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        p = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT_BENCH),
                "--dataset",
                str(_DATASET),
                "--out",
                str(out),
            ],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert p.returncode == 0, p.stderr + p.stdout
        doc = json.loads(out.read_text(encoding="utf-8"))
        jsonschema.validate(instance=doc, schema=schema)
        rows = doc.get("rows") or []
        assert any(isinstance(r, dict) and "yang_2015_style_metrics" in r for r in rows)
    finally:
        out.unlink(missing_ok=True)
