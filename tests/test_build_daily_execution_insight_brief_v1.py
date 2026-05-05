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
    myeongni = {
        "schema": "myeongni_independent_lens_v0",
        "ts_utc": "2099-01-01T00:00:00Z",
        "scores": {"direction_score": 0.08, "confidence": 0.5},
        "myeongri_stream_outputs": {"state_id": 15, "run_id": "t"},
    }
    sasang = {
        "ts_utc": "2099-01-01T00:00:00Z",
        "scores": {"direction_score": 0.17, "confidence": 0.71},
        "sasang_stream_outputs": {
            "mapping_target": "sideways",
            "regime_hypothesis": "phase_transition",
            "machine_readables": {"heat_proxy": 0.5, "cold_proxy": 0.4},
        },
    }
    market_sasang = {
        "ts_utc": "2099-01-01T00:00:00Z",
        "human_commander_gate_v1": {"banner_ko": "[TRACK B]"},
        "state_vector_sasang_softmax": {
            "taeyang": 0.25,
            "soyang": 0.25,
            "taeeum": 0.25,
            "soeum": 0.25,
        },
        "uncertainty": {"composite_uncertainty": 0.5, "entropy_norm_4way": 1.0},
        "veto": {"force_hold": True, "reason_codes": ["TEST"]},
    }
    logos_ind = {
        "ts_utc": "2099-01-01T00:00:00Z",
        "scores": {"direction_score": -0.3, "confidence": 0.2},
        "evidence_refs": [{}],
        "narrative_snippet_guarded": "[#a]",
    }
    v2 = {
        "schema": "myeongri_core_v2_upgrade_v1",
        "b_track_notice": "[MKM-B-TRACK-NOTICE] test disclaimer " + "x" * 32,
        "output": {
            "size_multiplier_recommended": 0.75,
            "commander_overlay_multiplier": 0.75,
            "direction_override_allowed": False,
        },
        "jijangan_weighted_vector": {
            "elements": {
                "wood": 0.1,
                "fire": 0.2,
                "earth": 0.2,
                "metal": 0.25,
                "water": 0.25,
            }
        },
        "neutral_structure_metrics_v1": {
            "contract": "btrack_neutral_structure_v1",
            "structural_tension_v1": 0.42,
            "latent_energy_vector_4d": [0.25, 0.25, 0.25, 0.25],
        },
        "shinsal_impact_overlay": {"detected": [{"id": "gwaegang_like"}]},
        "shinsal_detection_logs": {
            "schema": "shinsal_detection_logs_v1",
            "entries": [
                {
                    "id": "gwaegang_like",
                    "pillar_key": "day",
                    "pillar_text": "경진",
                    "evidence_tag": "day_pillar_exact_match",
                }
            ],
        },
    }
    md = mod.build_markdown(
        brief_date_utc="2099-01-01",
        workspace_anchor="test",
        fusion=fusion,
        thin=thin,
        thin_path=Path("/x/thin.json"),
        fusion_path=Path("/x/fusion.json"),
        calendar_date="2099-01-01",
        myeongni=myeongni,
        myeongni_path=Path("/x/myeongni.json"),
        sasang=sasang,
        sasang_path=Path("/x/sasang.json"),
        market_sasang=market_sasang,
        market_sasang_path=Path("/x/market_sasang.json"),
        logos_independent=logos_ind,
        logos_independent_path=Path("/x/logos.json"),
        myeongri_v2_upgrade=v2,
        myeongri_v2_upgrade_path=Path("/x/myeongri_v2.json"),
    )
    assert "snippet line" in md
    assert "test narrative" in md
    assert "risk_multiplier_cap` = 0.5" in md or "= 0.5" in md
    assert "`thin_ok=True`" in md
    assert "`fusion_ok=True`" in md
    assert "### 1c)" in md
    assert "Myeongni" in md
    assert "0.08" in md
    assert "[TRACK B]" in md
    assert "HIGH_ENTROPY" not in md or "TEST" in md
    assert "[#a]" in md
    assert "### 1e)" in md
    assert "0.75" in md
    assert "gwaegang_like" in md
    assert '"myeongri_v2_upgrade": true' in md
    assert "/x/myeongri_v2.json" in md
    assert "neutral.structural_tension_v1" in md
    assert "commander_overlay_multiplier" in md


def test_build_markdown_section_1c_missing_lens_files(tmp_path):
    mod = _load()
    missing = tmp_path / "nope.json"
    md = mod.build_markdown(
        brief_date_utc="2099-01-02",
        workspace_anchor="t",
        fusion={},
        thin=None,
        thin_path=Path("/y/thin.json"),
        fusion_path=Path("/y/fusion.json"),
        calendar_date=None,
        myeongni=None,
        myeongni_path=missing,
        sasang=None,
        sasang_path=missing,
        market_sasang=None,
        market_sasang_path=missing,
        logos_independent=None,
        logos_independent_path=missing,
    )
    assert "*(missing — `" in md
    assert '"myeongni": false' in md
    assert '"myeongri_v2_upgrade": false' in md


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
