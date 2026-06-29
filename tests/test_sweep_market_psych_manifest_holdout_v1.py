# @MKM12-METADATA
# Type: Logic
# Purpose: Holdout manifest sweep helpers (B-track v2).
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.sweep_market_psych_manifest_holdout_v1 import (  # noqa: E402
    _candidate_manifests,
    _scale_weights,
)
from scripts.market_psych_sasang_axis_v2 import load_manifest  # noqa: E402


def test_scale_weights_preserves_other_axes() -> None:
    base = load_manifest()
    out = _scale_weights(base, "TY", ["greed_score"], 2.0)
    assert out["axis_raw_weights"]["TY"]["greed_score"] == pytest.approx(
        float(base["axis_raw_weights"]["TY"]["greed_score"]) * 2.0
    )
    assert out["axis_raw_weights"]["TE"]["fear_score"] == base["axis_raw_weights"]["TE"]["fear_score"]


def test_candidate_manifests_include_baseline() -> None:
    base = load_manifest()
    cands = _candidate_manifests(base)
    ids = [c["profile_id"] for c in cands]
    assert "baseline" in ids
    assert len(cands) >= 8


def test_sweep_runner_smoke() -> None:
    psych = _ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
    kospi = _ROOT / "research/market_data/kospi_daily_external_yf.csv"
    if not psych.is_file() or not kospi.is_file():
        pytest.skip("psych v2 or kospi csv missing")
    import subprocess

    out = _ROOT / "reports/tmp_manifest_holdout_sweep_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/sweep_market_psych_manifest_holdout_v1.py"),
            "--holdout-days",
            "30",
            "--out",
            str(out),
            "--write-candidate",
            str(_ROOT / "reports/tmp_manifest_candidate_test.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "market_psych_manifest_holdout_sweep_v1"
    assert doc.get("best_on_train", {}).get("profile_id")
    out.unlink(missing_ok=True)
    (_ROOT / "reports/tmp_manifest_candidate_test.json").unlink(missing_ok=True)
