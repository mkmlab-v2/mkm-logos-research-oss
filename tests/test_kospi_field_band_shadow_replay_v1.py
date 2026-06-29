"""Field band shadow replay — scale rule, veto flag, WF parity."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _fixture_eval() -> dict:
    rows = []
    for d, ret, actual, pred, prior, close in [
        ("2026-06-01", 1.0, "bull", "neutral", 2500.0, 2525.0),
        ("2026-06-02", 0.2, "bull", "bull", 2525.0, 2530.0),
        ("2026-06-03", -1.0, "bear", "bull", 2530.0, 2505.0),
        ("2026-06-04", -7.0, "bear", "neutral", 2505.0, 2330.0),
        ("2026-06-05", 2.0, "bull", "bull", 2330.0, 2377.0),
        ("2026-06-06", 0.5, "bull", "neutral", 2377.0, 2389.0),
        ("2026-06-07", -6.5, "bear", "neutral", 2389.0, 2234.0),
        ("2026-06-08", 8.0, "bull", "bull", 2234.0, 2413.0),
        ("2026-06-09", -0.5, "bear", "bull", 2413.0, 2401.0),
        ("2026-06-10", 1.5, "bull", "bull", 2401.0, 2437.0),
        ("2026-06-11", -5.5, "bear", "neutral", 2437.0, 2303.0),
        ("2026-06-12", 0.3, "bull", "neutral", 2303.0, 2310.0),
    ]:
        rows.append(
            {
                "session_date": d,
                "actual_direction": actual,
                "predicted_direction": pred,
                "daily_return_pct": ret,
                "prior_close": prior,
                "actual_close": close,
            }
        )
    return {"rows": rows}


def _fixture_calendar() -> dict:
    rows = []
    for d in [f"2026-06-{i:02d}" for i in range(1, 13)]:
        rows.append(
            {
                "session_date": d,
                "kospi_index_prophecy": {
                    "predicted_return_band_pct": [-2.0, 2.0],
                },
            }
        )
    return {"rows": rows}


def _fixture_fusion() -> dict:
    return {
        "fusion_resolution": {"conflict_ids": ["field_bear_vs_lens_bull_majority"]},
        "lenses": {"logos": {"direction_sign": "bear"}},
    }


def _fixture_field_tier2() -> dict:
    return {
        "policy": {
            "direction_unchanged": True,
            "vol_band_k": 1.5,
            "vol_window": 5,
            "shock_scale": 1.5,
            "conflict_shock_scale": 1.75,
        }
    }


def test_vol_widen_scale_on_shock_conflict_day():
    from scripts.run_kospi_field_band_shadow_replay_v1 import run_field_band_shadow_replay

    doc = run_field_band_shadow_replay(
        _fixture_eval(),
        _fixture_calendar(),
        _fixture_fusion(),
        field_tier2=_fixture_field_tier2(),
        sasang_tier2={"force_hold": True, "band_widen_only": True, "veto_reason_codes": ["x"]},
        band_wf=None,
        n_folds=4,
    )
    shock_rows = [r for r in doc["daily_rows"] if r.get("shock_day")]
    assert shock_rows
    widened = [r for r in shock_rows if r.get("widened")]
    assert widened
    assert all(r["band_scale"] > 1.0 for r in widened)
    assert all(r.get("execution_block") == "sasang_veto" for r in doc["daily_rows"])


def test_shadow_replay_schema_and_summary_keys():
    from scripts.run_kospi_field_band_shadow_replay_v1 import run_field_band_shadow_replay

    doc = run_field_band_shadow_replay(
        _fixture_eval(),
        _fixture_calendar(),
        _fixture_fusion(),
        field_tier2=_fixture_field_tier2(),
        n_folds=4,
    )
    assert doc["schema"] == "kospi_field_band_shadow_replay_v1"
    assert doc["research_only"] is True
    assert doc["auto_apply"] is False
    assert doc["send_gate"] == "HOLD"
    assert doc["arm_id"] == "band_conflict_vol_widen"
    assert "full_window" in doc["summary"]
    assert "holdout_pooled" in doc["summary"]


def test_wf_parity_on_disk_artifacts():
    from scripts.run_kospi_field_band_shadow_replay_v1 import run_field_band_shadow_replay
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    eval_p = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    cal_p = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
    fusion_p = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
    wf_p = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
    if not all(p.is_file() for p in (eval_p, cal_p, fusion_p, wf_p)):
        pytest.skip("disk artifacts missing")

    doc = run_field_band_shadow_replay(
        _read(eval_p),
        _read(cal_p),
        _read(fusion_p),
        field_tier2=_read(ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"),
        band_wf=_read(wf_p),
        n_folds=4,
    )
    parity = doc["summary"]["wf_parity"]
    assert parity["within_tolerance"] is True


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json").is_file(),
    reason="eval artifact missing",
)
def test_shadow_replay_cli_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_shadow_replay_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(cp.stdout.strip().splitlines()[-1])
    assert out["ok"] is True
    assert out["wf_parity"].get("within_tolerance") is True
    replay = json.loads((ROOT / "reports/kospi_field_band_shadow_replay_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert replay["ladder_stage"] == "L1_shadow_replay"
