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


def test_emitted_template_with_bundle_and_track_b_optionals_validates(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    vm = tmp_path / "manifest.json"
    vm.write_text('{"schema":"logos_vector_index_manifest_v1","x":1}', encoding="utf-8")
    ar = tmp_path / "ann.json"
    ar.write_text('{"schema":"logos_vector_index_ann_lite_build_report_v1"}', encoding="utf-8")
    qs = tmp_path / "smoke.json"
    qs.write_text('{"schema":"logos_vector_ann_lite_query_result_v1"}', encoding="utf-8")
    out = tmp_path / "distill_track_b.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--bundle-json",
            str(_BUNDLE_MIN),
            "--vector-manifest-json",
            str(vm),
            "--ann-lite-report-json",
            str(ar),
            "--ann-lite-query-smoke-json",
            str(qs),
            "--write-template",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    prov = doc.get("provenance") or {}
    assert "track_b_vector_manifest_sha256" in prov
    assert "track_b_ann_lite_report_sha256" in prov


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
    assert instance.get("version") == "1.0.2"
    assert (instance.get("review_gate") or {}).get("status") == "pending"


def test_review_gate_invalid_status_fails_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    from jsonschema import exceptions as jsonschema_exceptions

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
    instance["review_gate"] = {"status": "not_a_valid_enum_value"}
    v = jsonschema.Draft7Validator(schema)
    with pytest.raises(jsonschema_exceptions.ValidationError):
        v.validate(instance)


def test_review_gate_approved_snapshot_with_sha256_validates(tmp_path: Path) -> None:
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
    instance["review_gate"] = {
        "status": "approved_snapshot",
        "artifact_sha256": "a" * 64,
        "reason_code": "human_signoff",
        "reviewer_role": "commander",
    }
    jsonschema.Draft7Validator(schema).validate(instance)
