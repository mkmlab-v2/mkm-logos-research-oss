"""CONSTITUTION §1.2.2 pointer row presence tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_a_code_constitution_pointer_row_v1.py"
CONSTITUTION = ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"


def _load():
    spec = importlib.util.spec_from_file_location("ptr_check", CHECK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_constitution_has_pointer_section() -> None:
    mod = _load()
    text = CONSTITUTION.read_text(encoding="utf-8")
    report = mod.evaluate(text)
    assert report["summary"]["decision"] == "PASS_POINTER_ROW"


def test_pointer_check_cli(tmp_path: Path) -> None:
    out = tmp_path / "check.json"
    proc = subprocess.run(
        [sys.executable, str(CHECK), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out.is_file()
