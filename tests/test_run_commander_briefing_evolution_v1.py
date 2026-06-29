"""Regression: commander briefing evolution loads evening score v1 and v2 schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_commander_briefing_evolution_v1 import _load_recent_scores, run_evolution


def test_load_recent_scores_accepts_v1_and_v2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "briefing_log"
    log_dir.mkdir()
    v1 = {
        "schema": "commander_evening_briefing_score_v1",
        "prediction_scores": [{"prediction_id": "branch:test", "outcome": "neutral"}],
    }
    v2 = {
        "schema": "commander_evening_briefing_score_v2",
        "prediction_scores": [{"prediction_id": "branch:test2", "outcome": "aligned"}],
    }
    ribl = {
        "schema": "evening_multi_lens_score_v1",
        "prediction_scores": [{"prediction_id": "pred_x", "lens": "logos", "kind": "x", "outcome": "HIT"}],
    }
    (log_dir / "2026-05-28_evening_score_v1.json").write_text(json.dumps(v1), encoding="utf-8")
    (log_dir / "2026-05-29_evening_score_v1.json").write_text(json.dumps(v2), encoding="utf-8")
    (log_dir / "2026-05-30_evening_multi_lens_score_v1.json").write_text(json.dumps(ribl), encoding="utf-8")
    (log_dir / "ignored.json").write_text(json.dumps({"schema": "other"}), encoding="utf-8")

    import scripts.run_commander_briefing_evolution_v1 as mod

    monkeypatch.setattr(mod, "LOG_DIR", log_dir)
    scores = _load_recent_scores(days=7)
    schemas = {s.get("schema") for s in scores}
    assert schemas == {
        "commander_evening_briefing_score_v1",
        "commander_evening_briefing_score_v2",
        "evening_multi_lens_score_v1",
    }


def test_run_evolution_counts_v2_scores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "briefing_log"
    log_dir.mkdir()
    rules = tmp_path / "rules.json"
    rules.write_text("{}", encoding="utf-8")
    for day in ("2026-05-27", "2026-05-28"):
        doc = {
            "schema": "commander_evening_briefing_score_v2",
            "prediction_scores": [
                {"prediction_id": "branch:fusion_bull_watch_field_align", "outcome": "neutral"}
            ],
        }
        (log_dir / f"{day}_evening_score_v1.json").write_text(json.dumps(doc), encoding="utf-8")

    import scripts.run_commander_briefing_evolution_v1 as mod

    monkeypatch.setattr(mod, "LOG_DIR", log_dir)
    monkeypatch.setattr(mod, "RULES_PATH", rules)
    out = run_evolution(dry_run=True, lookback_days=7)
    assert out.get("n_evening_scores") == 2


def test_lens_kind_aggregate_ribl_only_excludes_legacy_btrack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "briefing_log"
    log_dir.mkdir()
    legacy = {
        "schema": "commander_evening_briefing_score_v2",
        "prediction_scores": [
            {"kind": "btrack_price_hypo", "outcome": "reject"},
            {"kind": "btrack_price_hypo", "outcome": "reject"},
            {"kind": "btrack_price_hypo", "outcome": "reject"},
        ],
    }
    ribl = {
        "schema": "evening_multi_lens_score_v1",
        "prediction_scores": [
            {
                "lens": "price_btrack",
                "kind": "multi_asset_directional",
                "price_axis": "FAIL",
            },
            {
                "lens": "price_btrack",
                "kind": "kospi_morning_action",
                "price_axis": "NEUTRAL_DRAW",
            },
            {
                "lens": "price_btrack",
                "kind": "multi_asset_directional",
                "price_axis": "HIT",
            },
        ],
    }
    (log_dir / "2026-05-30_evening_score_v1.json").write_text(json.dumps(legacy), encoding="utf-8")
    (log_dir / "2026-06-01_evening_multi_lens_score_v1.json").write_text(json.dumps(ribl), encoding="utf-8")

    import scripts.run_commander_briefing_evolution_v1 as mod

    monkeypatch.setattr(mod, "LOG_DIR", log_dir)
    monkeypatch.setattr(mod, "RULES_PATH", tmp_path / "rules.json")
    (tmp_path / "rules.json").write_text("{}", encoding="utf-8")
    out = run_evolution(dry_run=True, lookback_days=7)
    agg = out.get("lens_kind_aggregate") or {}
    assert "unknown" not in agg
    assert "price_btrack" in agg
    prop_lenses = {p.get("lens") for p in out.get("proposals") or [] if p.get("lens")}
    assert "unknown" not in prop_lenses
