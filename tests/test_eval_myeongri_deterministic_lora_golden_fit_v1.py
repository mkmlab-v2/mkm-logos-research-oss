"""Smoke: Pack 0-B golden JSONL schema-fit eval script (no GPU)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_EVAL = _ROOT / "scripts/eval_myeongri_deterministic_lora_golden_fit_v1.py"
_FIXTURE = _ROOT / "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl"


def test_eval_script_exists() -> None:
    assert _EVAL.is_file()


def test_eval_writes_report(tmp_path: Path) -> None:
    pytest.importorskip("jsonschema")
    out = tmp_path / "golden_fit.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_EVAL),
            "--input-jsonl",
            str(_FIXTURE),
            "--out",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "myeongri_deterministic_lora_golden_fit_report_v1"
    assert data.get("ok") is True
    assert data.get("adapter_repo_relative_ssot") == "storage/adapters/myeongri_deterministic_lora_v0"
    assert data.get("rows_total", 0) >= 1
