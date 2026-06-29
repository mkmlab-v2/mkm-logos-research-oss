"""A-code governor sign-off archive pack tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_governor_signoff_archive_pack_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("archive_pack", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_archive_pack_track_wall() -> None:
    mod = _load()
    doc = mod.build_pack()
    assert doc.get("rq_close_allowed") is False
    assert doc.get("track_a_auto_promotion") is False
    assert doc.get("research_only") is True
    assert "artifact_files" in doc
    summary = doc.get("summary") or {}
    assert "rq_close_gate_decision" in summary
    assert "closure_allowed" in summary
    assert "commander_close_recorded" in summary


def test_archive_pack_cli(tmp_path: Path) -> None:
    out_json = tmp_path / "pack.json"
    out_md = tmp_path / "pack.md"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out-json", str(out_json), "--out-md", str(out_md)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_governor_signoff_archive_pack_v1"
