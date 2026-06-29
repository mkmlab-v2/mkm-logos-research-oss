from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/ops_dynamical_bench_v1.schema.json"
EXAMPLE = ROOT / "docs/final/schemas/ops_dynamical_bench_v1.example.json"
RUNNER = ROOT / "scripts/run_ops_dynamical_bench_v1.py"


def test_ops_dynamical_bench_example_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    instance = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_run_ops_dynamical_bench_v1_exit_0_and_schema():
    jsonschema = pytest.importorskip("jsonschema")
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out_path = ROOT / "reports/ops_dynamical_bench_v1_latest.json"
    assert out_path.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["fractal_level"] == "L0_isomorphism"
    assert doc["domain"] == "ops_agent"
    link = doc.get("ty_sparsity_geumhwa_link_v1") or {}
    assert link.get("schema") == "ops_dynamical_ty_geumhwa_link_v1"
    assert link.get("auto_trigger_forbidden") is True
    assert "geumhwa_index" in link
