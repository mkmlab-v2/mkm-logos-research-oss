# @MKM12-METADATA
# Type: Logic
# Purpose: CLI resolve_general_prophecy_question_v1 mutates registry safely.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"
_SAMPLE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
_RESOLVE = _ROOT / "scripts" / "resolve_general_prophecy_question_v1.py"


@pytest.fixture(scope="module")
def _validator():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_resolve_cli_updates_binary_question(tmp_path, _validator) -> None:
    src = tmp_path / "reg.json"
    src.write_text(_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "out.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_RESOLVE),
            "-i",
            str(src),
            "-o",
            str(out),
            "--question-id",
            "demo.binary.sample_01",
            "--outcome",
            "false",
            "--notes",
            "pytest fixture resolution",
            "--evidence-uri",
            "https://example.com/evidence-page",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs
    q = next(x for x in doc["questions"] if x["question_id"] == "demo.binary.sample_01")
    assert q["resolution"]["status"] == "resolved"
    assert q["resolution"]["outcome_binary"] is False
    assert "pytest fixture" in q["resolution"]["resolver_notes"]
    assert "example.com" in q["resolution"]["evidence_uris"][0]


def test_resolve_cli_unknown_id_exits_nonzero() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_RESOLVE),
            "-i",
            str(_SAMPLE),
            "--stdout-only",
            "--question-id",
            "does.not.exist",
            "--outcome",
            "true",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 2
