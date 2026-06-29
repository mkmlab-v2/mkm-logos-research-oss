"""A-code weekly ops summary tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_weekly_ops_summary_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("weekly_ops", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_weekly_ops_summary_has_full_and_light() -> None:
    mod = _load()
    doc = mod.build_summary()
    profiles = doc.get("profiles") or {}
    assert profiles.get("weekly_full", {}).get("task_name")
    assert profiles.get("weekly_light", {}).get("skip_governor_bundle") is True


def test_weekly_ops_summary_cli(tmp_path: Path) -> None:
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out_md.is_file()
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_weekly_ops_summary_v1"
