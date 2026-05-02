# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for Logos deep research distill contract + placeholder runner.
# Keywords: logos, track_b, distill, schema

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_deep_research_distill_v1.schema.json"
_RUNNER = _ROOT / "scripts" / "run_lens_logos_deep_fusion.py"
_BACKLOG = _ROOT / "docs" / "final" / "LOGOS_DEEP_RESEARCH_TRACK_B_BACKLOG_V1.md"
_COMMANDER_AXES = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_DEEP_RESEARCH_COMMANDER_REPORT_AXES_V1.json"


def test_contract_and_schema_exist() -> None:
    assert _BACKLOG.is_file()
    assert _CONTRACT.is_file()
    doc = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    assert doc.get("artifact_schema") == "logos_deep_research_distill_v1"
    assert doc.get("artifact_json_schema") == "docs/final/schemas/logos_deep_research_distill_v1.schema.json"
    assert _SCHEMA.is_file()


def test_json_schema_is_valid_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_placeholder_runner_dry_run() -> None:
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--dry-run"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    assert "OK contract=" in cp.stdout


def test_commander_report_axes_v1_json() -> None:
    assert _COMMANDER_AXES.is_file()
    doc = json.loads(_COMMANDER_AXES.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_deep_research_commander_report_axes_v1"
    assert doc.get("hypothesis_tier") == "B"
    banners = doc.get("report_banner_required") or []
    assert "[TRACK B / HYPO]" in banners
    axes = doc.get("axes") or []
    assert len(axes) >= 5
    for ax in axes:
        assert "axis_id" in ax and "constitution_facts_pointers" in ax


_BUNDLE_MIN = _ROOT / "tests" / "fixtures" / "logos_corpus_graph_bundle_minimal_distill_v1.json"


def test_emitted_template_with_bundle_validates(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "distill_bundle.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--bundle-json",
            str(_BUNDLE_MIN),
            "--slice-id",
            "slice3_bundle_anchor",
            "--write-template",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    instance = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(instance)
    assert (
        instance["provenance"]["dedupe_bundle_key_sha256"]
        == "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    )
    assert (
        instance["provenance"]["input_manifest_sha256"]
        == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )


def test_emitted_template_validates_against_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "distill.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--write-template", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    instance = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(instance)
