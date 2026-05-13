# @MKM12-METADATA
# Type: Logic
# Purpose: Parse helper for recommended-chain neutral_bps sweep CLI
# Keywords: pytest, prophecy, sweep
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_chain_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "run_prophecy_btrack_recommended_eval_chain_v1.py"
    spec = importlib.util.spec_from_file_location("rec_chain_sweep_parse", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_neutral_bps_sweep_csv_commas_and_semicolons() -> None:
    m = _load_chain_module()
    assert m.parse_neutral_bps_sweep_csv("2, 2.5 ; 3") == [2.0, 2.5, 3.0]
    assert m.parse_neutral_bps_sweep_csv("8") == [8.0]


def test_nb_slug_float_string() -> None:
    m = _load_chain_module()
    assert m._nb_slug(2.5) == "2_5"
