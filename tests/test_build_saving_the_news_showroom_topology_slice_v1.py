"""build_saving_the_news_showroom_topology_slice_v1.py"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_saving_the_news_showroom_topology_slice_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_slice", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_topology_snapshot_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load()
    art = tmp_path / "artifacts"
    art.mkdir()
    matrix = {
        "headline_anchor": {"headline": "Test headline"},
        "final_action": {"action": "WATCH"},
        "conflict_resolver": {"conflict": False},
        "matrix_rows": [],
    }
    matrix_path = art / "saving_the_news_phase2_matrix_view_v1_latest.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    monkeypatch.setattr(mod, "ART", art)
    monkeypatch.setattr(mod, "MATRIX", matrix_path)
    monkeypatch.setattr(mod, "GATING", art / "missing.json")
    monkeypatch.setattr(mod, "OUT_TOPOLOGY", art / "topo.json")
    monkeypatch.setattr(mod, "OUT_PANEL", art / "panel.json")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    topo = mod.build_topology_snapshot(matrix, None, stale_hours=24, display_mode=mod.DISPLAY_INTERNAL)
    panel = mod.build_matrix_panel(matrix, None, None, None)
    (art / "topo.json").write_text(json.dumps(topo), encoding="utf-8")
    (art / "panel.json").write_text(json.dumps(panel), encoding="utf-8")
    topo = json.loads((art / "topo.json").read_text(encoding="utf-8"))
    assert topo["schema_version"] == "showroom_topology_radar_snapshot_v1"
    assert topo["no_trade_signals"] is True
    panel = json.loads((art / "panel.json").read_text(encoding="utf-8"))
    assert panel["schema"] == "saving_the_news_matrix_panel_slice_v1"
    assert "layer_b" in panel
