# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCR = _ROOT / "scripts" / "build_daily_execution_insight_brief_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_daily_execution_insight_brief_v1", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_daily_execution_insight_brief_v1"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_build_markdown_embeds_fusion_and_snippet(tmp_path):
    mod = _load()
    fusion = {
        "conflict_summary": {
            "conflict_narrative_guarded": "test narrative",
            "minority_lens_ids": ["logos"],
            "logos_evidence_verse_ids": ["v1"],
        }
    }
    thin = {
        "rows": [
            {
                "calendar_date": "2099-01-01",
                "lens_outputs": {
                    "logos_dual_regime": {
                        "interpretation_snippet": "snippet line",
                        "risk_multiplier_cap": 0.5,
                        "market_shock_confirmed": False,
                        "veto_triggered": True,
                    }
                },
            }
        ]
    }
    md = mod.build_markdown(
        brief_date_utc="2099-01-01",
        workspace_anchor="test",
        fusion=fusion,
        thin=thin,
        thin_path=Path("/x/thin.json"),
        fusion_path=Path("/x/fusion.json"),
        calendar_date="2099-01-01",
    )
    assert "snippet line" in md
    assert "test narrative" in md
    assert "risk_multiplier_cap` = 0.5" in md or "= 0.5" in md
    assert "_thin_ok=True" in md
    assert "fusion_ok=True" in md


def test_pick_row_fallback_last_populated():
    mod = _load()
    rep = {
        "rows": [
            {"calendar_date": "2020-01-01", "lens_outputs": {"logos_dual_regime": None}},
            {
                "calendar_date": "2020-02-01",
                "lens_outputs": {"logos_dual_regime": {"interpretation_snippet": "z"}},
            },
        ]
    }
    row, dk = mod._pick_thin_row(rep, None)
    assert dk == "2020-02-01"
    assert row["lens_outputs"]["logos_dual_regime"]["interpretation_snippet"] == "z"


def test_main_writes_file(tmp_path, monkeypatch):
    mod = _load()
    fusion_p = tmp_path / "fusion.json"
    thin_p = tmp_path / "thin.json"
    out_p = tmp_path / "out.md"
    fusion_p.write_text(
        json.dumps(
            {
                "conflict_summary": {
                    "conflict_narrative_guarded": "n",
                    "minority_lens_ids": [],
                    "logos_evidence_verse_ids": [],
                }
            }
        ),
        encoding="utf-8",
    )
    thin_p.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "calendar_date": "2030-06-15",
                        "lens_outputs": {
                            "logos_dual_regime": {
                                "interpretation_snippet": "s",
                                "risk_multiplier_cap": 1.0,
                                "market_shock_confirmed": False,
                                "veto_triggered": False,
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "_utc_date_today", lambda: "2030-06-15")
    monkeypatch.setattr(sys, "argv", ["x", "--fusion-json", str(fusion_p), "--thin-json", str(thin_p), "--out", str(out_p)])
    mod.main()
    assert out_p.is_file()
    txt = out_p.read_text(encoding="utf-8")
    assert "s" in txt
    assert "n" in txt
