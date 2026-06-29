"""A-code 12AI matrix v2 sandbox — schema, pathology cross-ref, eval contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MATRIX_SCHEMA = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.schema.json"
MATRIX_EXAMPLE = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json"
PATHOLOGY_V25 = ROOT / "docs/final/protocols/A_CODE_12AI_CLINICAL_PATHOLOGY_MATRIX_V2_5.json"
EVAL_CONTRACT = ROOT / "experiments/a_code_12ai_v2/specs/a_code_eval_axes_contract_v2.json"
VALIDATE_CLI = ROOT / "scripts/validate_a_code_12ai_matrix_v2.py"

FORBIDDEN_EVAL_KEYS = (
    "price_directional_hit_rate",
    "jaccard",
    "saving_pct",
    "live_trading",
    "dual_axis_beat",
)


def test_a_code_matrix_example_validates_against_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(MATRIX_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(MATRIX_EXAMPLE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("rq_id") == "RQ-028"
    assert len(doc.get("cells") or []) == 12
    assert doc.get("research_only") is True


def test_pathology_v25_has_twelve_cells_and_principles() -> None:
    doc = json.loads(PATHOLOGY_V25.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_12ai_clinical_pathology_matrix_v2_5"
    assert len(doc.get("cells") or []) == 12
    assert "seongjeong_bulbyeon" in (doc.get("core_principles") or {})
    assert doc.get("research_only") is True


def test_eval_contract_forbids_track_a_and_price_keys() -> None:
    contract = json.loads(EVAL_CONTRACT.read_text(encoding="utf-8"))
    forbidden = set(contract.get("forbidden_metric_keys") or [])
    for key in FORBIDDEN_EVAL_KEYS:
        assert key in forbidden


def test_validate_cli_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "validation_report.json"
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_CLI), "--json-out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report.get("ok") is True
    assert report.get("rq_id") == "RQ-028"
