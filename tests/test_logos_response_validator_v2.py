"""Contract tests for logos_response_v2 auto-schema behavior."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "logos_response_v2_valid_min.json"
SCRIPT = ROOT / "scripts" / "logos_response_validator_v1.py"

pytest.importorskip("jsonschema")


def test_validate_v2_fixture_auto_schema_ok() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", "--input", str(FIXTURE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "logos_response_v2" in r.stdout


def test_v2_banned_phrase_in_denomination_field_fails() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["denominational_view"][0]["interpretation_summary"] = "이 해석은 무조건 맞다."
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "validate", "--input", tmp],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 2
        assert "denominational_view" in r.stderr or "BANNED_FAIL" in r.stderr
    finally:
        Path(tmp).unlink(missing_ok=True)
