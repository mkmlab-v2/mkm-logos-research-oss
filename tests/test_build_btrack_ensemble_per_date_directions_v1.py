# @MKM12-METADATA
# Type: Logic
# Purpose: per-date ensemble direction builder smoke
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BUILD = _ROOT / "scripts" / "build_btrack_ensemble_per_date_directions_v1.py"
_BUNDLE = _ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
_CFG = _ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
_SCORE = _ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
_BTC = _ROOT / "research/market_data/btc_daily_external_yf.csv"


def test_build_per_date_directions_script_exists() -> None:
    assert _BUILD.is_file()


def test_build_v2_per_date_directions(tmp_path: Path) -> None:
    for p in (_BUNDLE, _CFG, _SCORE, _BTC):
        if not p.is_file():
            import pytest

            pytest.skip(f"missing prerequisite: {p}")
    out = tmp_path / "dirs.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--bundle-json",
            str(_BUNDLE),
            "--ensemble-config",
            str(_CFG),
            "--score-json",
            str(_SCORE),
            "--btc-csv",
            str(_BTC),
            "--ensemble-mode",
            "v2_confidence_fusion",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_ensemble_per_date_directions_v1"
    rows = doc.get("rows") or []
    assert len(rows) >= 5
    assert all(r.get("predicted_direction") in ("bull", "bear", "neutral") for r in rows)
    assert doc.get("ensemble_mode") == "v2_confidence_fusion"
