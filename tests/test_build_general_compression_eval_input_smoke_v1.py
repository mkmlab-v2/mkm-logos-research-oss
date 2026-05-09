"""Smoke: general_compression eval input builds with at least one case (manifest JSONL or V2 fallback)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_general_compression_eval_input_non_empty() -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_general_compression_eval_input.py")]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr + cp.stdout

    out_path = ROOT / "docs" / "final" / "artifacts" / "general_compression_eval_input_v1.json"
    assert out_path.is_file(), str(out_path)
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    cases = doc.get("compression_cases") or []
    assert isinstance(cases, list)
    assert len(cases) >= 1, "expected manifest rows or fallback V2 compression_cases"

