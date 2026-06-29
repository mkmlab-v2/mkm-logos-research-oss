"""Offline gate for mkm_ui_shell_contract_v1.json."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_mkm_ui_shell_contract_v1.py"
    spec = importlib.util.spec_from_file_location("check_mkm_ui_shell_contract_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_ui_shell_contract_gate_passes(tmp_path: Path):
    mod = _load()
    out = tmp_path / "gate.json"
    code, report = mod.run_check(write_report=True, out_path=out)
    assert code == 0, report
    assert report["overall_ok"] is True
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["overall_ok"] is True
    assert saved["consumer_portal_v1"]["ok"] is True
    assert saved["operator_console_v1"]["ok"] is True
