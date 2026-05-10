from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/lens_music_internal_eval_sessions_sample_v1.jsonl"
SCRIPT = ROOT / "scripts/validate_lens_music_internal_eval_jsonl_v1.py"


def test_validate_jsonl_smoke_fixture_passes():
    pytest.importorskip("jsonschema")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--jsonl", str(FIXTURE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = json.loads(r.stdout.strip())
    assert out["ok"] is True
    assert out["rows_validated"] == 2


def test_validate_jsonl_rejects_invalid_row(tmp_path):
    pytest.importorskip("jsonschema")
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"not":"schema"}\n', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--jsonl", str(bad)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
