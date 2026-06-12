"""Phase-1 gate for universe_hub_v2 scaffold."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_mkm_universe_hub_shell_v2.py"
    spec = importlib.util.spec_from_file_location("check_mkm_universe_hub_shell_v2", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_universe_hub_v2_scaffold_gate_passes(tmp_path: Path):
    mod = _load()
    out = tmp_path / "gate.json"
    code, report = mod.run_check(write_report=True, out_path=out)
    assert code == 0, report
    assert report["overall_ok"] is True
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["phase"] == "P4_embed_scaffold_complete_local"
