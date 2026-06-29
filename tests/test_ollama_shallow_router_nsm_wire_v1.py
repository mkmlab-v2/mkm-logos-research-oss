"""NSM prime tag wire for Ollama shallow router (Phase 11-C)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_example_json_has_nsm_prime_tags():
    example = json.loads(
        (ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json").read_text(encoding="utf-8")
    )
    tags = example.get("nsm_prime_tags")
    assert isinstance(tags, list)
    assert 1 <= len(tags) <= 3


def test_example_validates_with_nsm_tags():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.schema.json").read_text(encoding="utf-8")
    )
    example = json.loads(
        (ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=example, schema=schema)


def test_enrich_infers_tags_for_logos():
    from scripts.ollama_shallow_router_nsm_v1 import enrich_shallow_output, nsm_wire_ok

    out = enrich_shallow_output(
        {
            "schema": "ollama_shallow_router_output_v1",
            "research_only": True,
            "send_gate": "HOLD",
            "domain_tag": "logos",
            "coordinates": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
            "anchor_ids": [],
            "parse_status": "raw",
        },
        input_text="성경 Logos verse scripture shallow tagging",
    )
    assert nsm_wire_ok(out)
    assert "words" in out["nsm_prime_tags"]


def test_handoff_carries_nsm_tags():
    example = ROOT / "docs/final/schemas/ollama_shallow_router_output_v1.example.json"
    out = ROOT / "reports/ollama_shallow_router_handoff_nsm_wire_test_latest.json"
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
    assert doc.get("nsm_prime_tags")
    assert doc.get("layer_a_gate_hint", {}).get("nsm_prime_tags")


def test_offline_bench_nsm_wire_rate():
    proc = subprocess.run(
        [sys.executable, "scripts/build_ollama_shallow_nsm_wire_offline_bench_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(
        (ROOT / "reports/ollama_shallow_router_bench_nsm_wire_offline_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["raw"]["nsm_wire_ok_rate"] == 1.0
