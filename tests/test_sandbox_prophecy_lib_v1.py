from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lib():
    spec = importlib.util.spec_from_file_location(
        "sandbox_prophecy_lib_v1", ROOT / "scripts/sandbox_prophecy_lib_v1.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_tag_hypothesis_sandbox() -> None:
    lib = _lib()
    doc = {
        "schema": "btrack_hypothesis_prophecy_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": "[HYPO] test",
        "prediction": {"instrument": "btc", "horizon": "1d", "direction": "neutral"},
    }
    out = lib.tag_hypothesis_sandbox(doc, target_id="btc_v1_price_only", lens_profile="v1_price_only")
    assert out["hypothesis_tier"] == "SANDBOX"
    assert "[SANDBOX]" in out["label"]
    assert out["sandbox_meta"]["track_wall"]["prod_score_mutation"] is False


def test_default_targets_includes_eth_and_kospi() -> None:
    lib = _lib()
    ids = {t["target_id"] for t in lib.default_targets()}
    assert "eth_v1_price_only" in ids
    assert "eth_v1_myeongni_sasang" in ids
    assert "kospi_v1_myeongni_sasang" in ids
    assert "btc_v2_confidence_fusion" in ids
    assert "sol_v1_price_only" in ids
    assert "gld_v1_price_only" in ids
    assert "btc_v2_price_macro_news" in ids
    assert "kospi_v1_price_only" in ids
    assert len(lib.default_targets()) >= 11
    all_ids = {t["target_id"] for t in lib.all_targets()}
    assert "btc_phase3_funding_skew" in all_ids
    assert "ndx_v1_price_only" in all_ids
    assert len(lib.all_targets()) >= 27
    assert "btc_phase3_funding_skew_invert" in all_ids
    assert "btc_phase3_funding_skew_db01" in all_ids
    assert "btc_phase3_funding_skew_db02" in all_ids
    assert "btc_sasang_heat_cold_sign" in all_ids
    assert "qqq_v1_price_only" in all_ids


def test_phase3_sensor_eval_on_fixture(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "sandbox_phase3_sensor_eval_v1",
        ROOT / "scripts/sandbox_phase3_sensor_eval_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    p = tmp_path / "joined.jsonl"
    rows = [
        {
            "eval_date": "2026-05-01",
            "instrument": "btc",
            "actual_direction": "bull",
            "sensors": {"perp_funding_skew_signed_flow_z": 0.5},
        },
        {
            "eval_date": "2026-05-02",
            "instrument": "btc",
            "actual_direction": "bear",
            "sensors": {"perp_funding_skew_signed_flow_z": -0.3},
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    m = mod.eval_phase3_sensor(p, sensor_z_key="perp_funding_skew_signed_flow_z", recent_trading_days=30)
    assert m["n_evaluated"] == 2
    assert m["price_hits"] == 2
