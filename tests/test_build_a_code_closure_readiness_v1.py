"""A-code closure readiness tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_closure_readiness_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("closure_ready", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_closure_readiness_commander_close_gate() -> None:
    mod = _load()
    doc = mod.build()
    checks = {c.get("check"): c.get("ok") for c in doc.get("checks") or []}
    if doc.get("mechanics_bundle_ok") and not checks.get("commander_close_artifact"):
        assert doc.get("closure_allowed") is False
    if checks.get("commander_close_artifact"):
        assert doc.get("closure_allowed") is True


def test_closure_readiness_cli(tmp_path: Path) -> None:
    out = tmp_path / "ready.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_closure_readiness_v1"
