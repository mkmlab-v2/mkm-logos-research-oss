"""Tests for build_logos_response_retry_inputs_v1 script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_response_retry_inputs_v1.py"
VALIDATOR = ROOT / "scripts" / "logos_response_validator_v1.py"


def test_build_retry_inputs_and_validate(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    retry = tmp_path / "retry.txt"
    mkm_src = ROOT / "docs" / "final" / "artifacts" / "mkm_logos_response_v2_latest.json"

    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mkm-json",
            str(mkm_src),
            "--output-raw",
            str(raw),
            "--output-retry",
            str(retry),
            "--raw-format",
            "fenced",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert raw.is_file()
    assert retry.is_file()

    # Raw is fenced/noisy text, but pipeline should parse & validate.
    p = subprocess.run(
        [sys.executable, str(VALIDATOR), "pipeline", "-i", str(raw)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr
    assert "성경 고도화 해석 브리핑" in p.stdout

    # Retry is strict JSON and should validate directly.
    v = subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", "-i", str(retry)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert v.returncode == 0, v.stderr
    # Also ensure schema field is v2.
    doc = json.loads(retry.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_response_v2"
