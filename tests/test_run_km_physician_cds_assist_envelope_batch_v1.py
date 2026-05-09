# -*- coding: utf-8 -*-
# Purpose: JSONL batch runner produces valid envelopes for example payloads.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_IN = _ROOT / "tests" / "fixtures" / "km_physician_cds_assist_payload_batch_v1.example.jsonl"
_BATCH_SCRIPT = _ROOT / "scripts" / "run_km_physician_cds_assist_envelope_batch_v1.py"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "km_physician_cds_assist_envelope_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_batch_example_jsonl_all_ok(tmp_path) -> None:
    out = tmp_path / "out.jsonl"
    r = subprocess.run(
        [sys.executable, str(_BATCH_SCRIPT), "--in", str(_FIXTURE_IN), "--out", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    for line in lines:
        doc = json.loads(line)
        assert doc.get("ok") is True
        env = doc.get("envelope")
        assert isinstance(env, dict)
        jsonschema.Draft7Validator(schema).validate(env)


def test_batch_fail_fast(tmp_path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"id":"x","clinical_question":"ab","evidence_assessment":"sufficient"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    r = subprocess.run(
        [sys.executable, str(_BATCH_SCRIPT), "--in", str(bad), "--out", str(out), "--fail-fast"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2
    assert not out.exists() or out.read_text().strip() == ""
