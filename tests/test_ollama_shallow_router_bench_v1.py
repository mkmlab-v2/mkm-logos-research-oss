"""Ollama shallow router v1 — schema, bench offline, JSON extract helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_shallow_router_output_example_validates() -> None:
    schema_path = ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    example = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)


def test_golden_fixture_count() -> None:
    doc = json.loads((ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json").read_text(encoding="utf-8"))
    fixtures = doc.get("fixtures", [])
    assert len(fixtures) >= 8


def test_extract_json_object_brace_block() -> None:
    from scripts.run_ollama_shallow_router_bench_v1 import _extract_json_object

    text = 'noise {"schema":"ollama_shallow_router_output_v1","domain_tag":"logos"} tail'
    parsed = _extract_json_object(text)
    assert parsed is not None
    assert parsed["domain_tag"] == "logos"


def test_bench_skip_ollama_exit0() -> None:
    out = ROOT / "reports/ollama_shallow_router_bench_v1_test_skip_latest.json"
    if out.exists():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_ollama_shallow_router_bench_v1.py",
            "--skip-ollama",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ollama_shallow_router_bench_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["mode"] == "skipped"


def test_handoff_from_example_exit0() -> None:
    example = ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json"
    out = ROOT / "reports/ollama_shallow_router_handoff_v1_test_latest.json"
    if out.exists():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_ollama_shallow_router_handoff_v1.py",
            "--input-json",
            str(example),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ollama_shallow_router_handoff_v1"
    assert doc["lens_route_hint"]["lens_id"] == "logos"


def test_thermo_leak_detector() -> None:
    from scripts.run_ollama_shallow_router_bench_v1 import _has_thermo_leak

    assert _has_thermo_leak('{"E_i": 1}')
    assert not _has_thermo_leak('{"S":0.25,"L":0.25,"K":0.25,"M":0.25}')
