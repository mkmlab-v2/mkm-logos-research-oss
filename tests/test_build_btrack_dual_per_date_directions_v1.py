# @MKM12-METADATA
# Type: Logic
# Purpose: dual per-date direction merge smoke
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BUILD = _ROOT / "scripts/build_btrack_dual_per_date_directions_v1.py"
_BUNDLE = _ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
_CFG = _ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
_BTC = _ROOT / "research/market_data/btc_daily_external_yf.csv"
_KOSPI = _ROOT / "research/market_data/kospi_daily_external_yf.csv"


def test_dual_per_date_build_script_exists() -> None:
    assert _BUILD.is_file()


def test_build_dual_per_date_directions_smoke(tmp_path: Path) -> None:
    for p in (_BUNDLE, _CFG, _BTC, _KOSPI):
        if not p.is_file():
            import pytest

            pytest.skip(f"missing prerequisite: {p}")
    dual_out = tmp_path / "dual.json"
    btc_out = tmp_path / "btc_legacy.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--recent-trading-days",
            "3",
            "--dual-output",
            str(dual_out),
            "--btc-legacy-output",
            str(btc_out),
            "--work-dir",
            str(tmp_path / "work"),
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(dual_out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_ensemble_per_date_directions_dual_v1"
    rows = doc.get("rows") or []
    assert len(rows) >= 4
    insts = {str(r.get("instrument")) for r in rows}
    assert "kospi" in insts and "btc" in insts
    assert all(r.get("predicted_direction") in ("bull", "bear", "neutral") for r in rows)
    assert btc_out.is_file()
