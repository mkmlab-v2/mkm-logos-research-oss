"""Smoke tests for NotebookLM minimal portfolio status builder."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json"


def test_portfolio_json_loads_and_has_pin_daily():
    data = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    assert data["schema"] == "notebooklm_minimal_portfolio_v1"
    notebooks = data["notebooks"]
    keys = {n["key"] for n in notebooks}
    assert "00_OPS" in keys
    assert "24_TRACKC" in keys
    assert "99_ARCHIVE" in keys
    assert len(data["usage_tiers"]["pin_daily"]) == 2


def test_portfolio_status_script_runs(tmp_path, monkeypatch):
    import scripts.build_notebooklm_minimal_portfolio_status_v1 as mod

    out_json = tmp_path / "status.json"
    out_md = tmp_path / "status.md"
    monkeypatch.setattr(mod, "OUT_JSON", out_json)
    monkeypatch.setattr(mod, "OUT_MD", out_md)
    monkeypatch.setattr(mod, "NOTEBOOK_MAP", tmp_path / "notebook_ids.json")

    rc = mod.build_status(write_notebook_map=True, skip_live_counts=True)
    assert rc == 0
    assert out_json.is_file()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["schema"] == "notebooklm_portfolio_status_v1"
    assert len(payload["notebooks"]) >= 10
