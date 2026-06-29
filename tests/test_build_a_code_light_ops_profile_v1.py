"""A-code light ops profile tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_light_ops_profile_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("light_profile", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_light_profile_skips_governor() -> None:
    mod = _load()
    doc = mod.build_profile()
    assert doc.get("skip_governor_bundle") is True
    assert doc.get("weekly_task_name") == "MKM-ACode-OperatorAssistLane-Weekly-Light"
    assert doc.get("track_wall", {}).get("track_a_auto_promotion") is False


def test_light_profile_cli(tmp_path: Path) -> None:
    out = tmp_path / "profile.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_light_ops_profile_v1"
