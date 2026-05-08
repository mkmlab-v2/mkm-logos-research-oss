"""Contract tests for logos_response_validator_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "logos_response_v1_valid_min.json"
SCRIPT = ROOT / "scripts" / "logos_response_validator_v1.py"
SCHEMA = ROOT / "docs" / "final" / "artifacts" / "schemas" / "logos_response_schema_v1.json"


pytest.importorskip("jsonschema")


def test_validate_fixture_ok() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", "--input", str(FIXTURE), "--schema", str(SCHEMA)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_banned_word_in_final_insight_fails() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["final_insight_non_gating"] = "이것은 무조건 옳다."
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(doc, f, ensure_ascii=False)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "validate", "--input", tmp, "--schema", str(SCHEMA)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 2
        assert "banned_phrase" in r.stderr or "BANNED_FAIL" in r.stderr
    finally:
        Path(tmp).unlink(missing_ok=True)
