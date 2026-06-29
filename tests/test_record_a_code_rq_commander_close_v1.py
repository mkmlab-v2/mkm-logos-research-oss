"""A-code commander close record tests."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "scripts/record_a_code_rq_commander_close_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("a_code_close", RECORD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_record_requires_human_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mod = _load()
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps({"summary": {"mechanical_close_candidate": True}}),
        encoding="utf-8",
    )
    archive = tmp_path / "archive.json"
    archive.write_text(json.dumps({"archive_ready": True}), encoding="utf-8")
    monkeypatch.setattr(mod, "DEFAULT_GATE", gate)
    monkeypatch.setattr(mod, "DEFAULT_ARCHIVE", archive)
    monkeypatch.delenv("MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED", raising=False)
    with pytest.raises(ValueError, match="MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED"):
        mod.build(close_reference="TEST-REF")


def test_record_build_with_human_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mod = _load()
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps({"summary": {"mechanical_close_candidate": True}}),
        encoding="utf-8",
    )
    archive = tmp_path / "archive.json"
    archive.write_text(json.dumps({"archive_ready": True}), encoding="utf-8")
    monkeypatch.setattr(mod, "DEFAULT_GATE", gate)
    monkeypatch.setattr(mod, "DEFAULT_ARCHIVE", archive)
    monkeypatch.setenv("MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED", "1")
    doc = mod.build(close_reference="COMMANDER-TEST-REF")
    assert doc.get("rq_status") == "CLOSED"
    assert doc.get("rq_028_closed") is True
    assert "Track A" in (doc.get("explicit_not_promoted") or [""])[0]


def test_record_cli(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps({"summary": {"mechanical_close_candidate": True}}),
        encoding="utf-8",
    )
    archive = tmp_path / "archive.json"
    archive.write_text(json.dumps({"archive_ready": True}), encoding="utf-8")

    out = tmp_path / "close.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(RECORD),
            "--out",
            str(out),
            "--close-reference",
            "COMMANDER-TEST-CLI",
            "--gate-path",
            str(gate),
            "--archive-path",
            str(archive),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED": "1"},
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_commander_close_v1"
