"""RQ-028 P7 evidence pack tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK_SCRIPT = ROOT / "scripts/build_a_code_governor_evidence_pack_v1.py"
GATE = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"


def _load_pack_module():
    spec = importlib.util.spec_from_file_location("a_code_evidence_pack", PACK_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_evidence_pack_builds_watch_status() -> None:
    if not GATE.is_file():
        pytest.skip("promotion gate missing")
    mod = _load_pack_module()
    pack = mod.build_pack(run_pytest=False)
    assert pack.get("schema") == "a_code_governor_evidence_pack_v1"
    assert pack.get("rq_id") == "RQ-028"
    assert pack.get("research_only") is True
    assert pack.get("human_sign_off_required") is True
    assert pack.get("track_a_auto_promotion") is False
    assert pack.get("status") in {"WATCH", "HOLD_RESEARCH"}
    assert pack.get("profile_validation", {}).get("ok") is True


def test_evidence_pack_cli_writes_json(tmp_path: Path) -> None:
    if not GATE.is_file():
        pytest.skip("promotion gate missing")
    out = tmp_path / "pack.json"
    proc = subprocess.run(
        [sys.executable, str(PACK_SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "reproduction_commands" in doc
    assert len(doc["reproduction_commands"]) >= 5
