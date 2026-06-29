"""Prophecy lens combo backtest — Science Core arms [HYPO][research_only]."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_science_variants_extend_universe() -> None:
    from scripts.run_prophecy_lens_combo_backtest_v1 import _build_variants

    base = _build_variants(include_science=False)
    sci = _build_variants(include_science=True)
    assert len(sci) == len(base) + 4
    ids = {v["id"] for v in sci}
    assert "science" in ids
    assert "science+sasang" in ids
    assert "science+myeongni" in ids
    assert "science+logos" in ids


def test_extract_science_maps_session_date(tmp_path: Path) -> None:
    from scripts.run_prophecy_lens_combo_backtest_v1 import _extract_science_maps

    p = tmp_path / "sci.jsonl"
    _write_jsonl(
        p,
        [
            {
                "session_date": "2026-06-01",
                "direction": "bull",
                "scores": {"direction_score": 0.42},
            },
            {
                "eval_date": "2026-06-02",
                "direction": "bear",
                "scores": {"direction_score": -0.31},
            },
        ],
    )
    signs, scores = _extract_science_maps(p)
    assert signs["2026-06-01"] == 1
    assert signs["2026-06-02"] == -1
    assert scores["2026-06-01"] == pytest.approx(0.42)
    assert scores["2026-06-02"] == pytest.approx(-0.31)


def test_science_only_variant_uses_per_date_sign() -> None:
    from scripts.run_prophecy_lens_combo_backtest_v1 import _simulate_variant

    rows = [
        {
            "eval_date": "2026-06-01",
            "instrument": "kospi",
            "actual_direction": "bull",
            "daily_return": 0.01,
        },
        {
            "eval_date": "2026-06-02",
            "instrument": "kospi",
            "actual_direction": "bear",
            "daily_return": -0.01,
        },
    ]
    variant = {"id": "science", "lenses": ["science"], "use_coordinator": False, "resolver": "science_only"}
    out = _simulate_variant(
        variant=variant,
        rows=rows,
        btc_prior={},
        myeongni_map={},
        sasang_map={},
        science_sign_map={"2026-06-01": 1, "2026-06-02": -1},
        science_score_map={"2026-06-01": 0.5, "2026-06-02": -0.5},
        logos_sign=0,
        logos_confidence=0.0,
        logos_vote_mode="omit",
        logos_min_confidence=0.25,
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    assert out["metrics"]["n_active_days"] == 2
    assert out["metrics"]["directional_hit_rate_active"] == pytest.approx(1.0)


def test_science_blend_respects_combo_weights() -> None:
    from scripts.run_prophecy_lens_combo_backtest_v1 import _simulate_variant

    rows = [
        {
            "eval_date": "2026-06-01",
            "instrument": "kospi",
            "actual_direction": "bull",
            "daily_return": 0.02,
        }
    ]
    variant = {
        "id": "science+sasang",
        "lenses": ["science", "sasang"],
        "use_coordinator": False,
        "resolver": "science_blend",
        "science_weight": 0.55,
        "humanist_weight": 0.45,
        "humanist_leg": "sasang",
    }
    out = _simulate_variant(
        variant=variant,
        rows=rows,
        btc_prior={},
        myeongni_map={},
        sasang_map={"2026-06-01": 1},
        science_sign_map={"2026-06-01": 1},
        science_score_map={"2026-06-01": 0.8},
        logos_sign=0,
        logos_confidence=0.0,
        logos_vote_mode="omit",
        logos_min_confidence=0.25,
        fee_rate=0.0,
        deadzone=0.001,
        annual_trading_days=252,
    )
    assert out["metrics"]["n_active_days"] == 1


def test_main_cli_science_core_smoke(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    sidecar = tmp_path / "sidecar.json"
    sci = tmp_path / "sci.jsonl"
    out = tmp_path / "out.json"

    score.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "eval_date": "2026-06-01",
                        "instrument": "kospi",
                        "actual_direction": "bull",
                        "daily_return": 0.01,
                    },
                    {
                        "eval_date": "2026-06-02",
                        "instrument": "kospi",
                        "actual_direction": "neutral",
                        "daily_return": 0.0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    sidecar.write_text(
        json.dumps(
            {
                "lens_globals_for_sidecar": {"logos": {"direction_score": 0.0, "confidence": 0.1}},
                "per_date_features": [],
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        sci,
        [
            {"session_date": "2026-06-01", "direction": "bull", "scores": {"direction_score": 0.3}},
            {"session_date": "2026-06-02", "direction": "neutral", "scores": {"direction_score": 0.0}},
        ],
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_prophecy_lens_combo_backtest_v1.py"),
            "--score-json",
            str(score),
            "--sidecar-json",
            str(sidecar),
            "--science-jsonl",
            str(sci),
            "--target-instrument",
            "kospi",
            "--include-science-core",
            "--logos-vote-mode",
            "omit",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_lens_combo_backtest_v1"
    assert doc["inputs"]["include_science_core"] is True
    assert doc["inputs"]["science_map_dates"] == 2
    ids = {s["strategy_id"] for s in doc["ranked_strategies"]}
    assert "science+sasang" in ids
