"""MDD safeguard integrity for kernel v2 market arms (B-track)."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.ijeoma_kernel_v2_mdd_safeguard_holdout_lib_v1 as lib


def test_prereg_schema() -> None:
    doc = lib.load_prereg()
    assert doc["schema"] == "ijeoma_kernel_v2_mdd_safeguard_holdout_prereg_v1"
    assert "P13_kernel_v2_bomyung_grid_best" in (doc.get("challenger_arms") or [])


def test_max_drawdown_monotonic_on_losses() -> None:
    curve = [1.0, 0.9, 0.8, 0.85, 0.7]
    assert abs(lib._max_drawdown(curve) - 0.3) < 1e-9


def test_bomyung_fuse_reduces_active_exposure(tmp_path: Path) -> None:
    per_date = tmp_path / "per_date.jsonl"
    kospi = tmp_path / "kospi.csv"
    rows = []
    klines = ["date,close"]
    price = 100.0
    for i in range(120):
        d = f"2026-01-{(i % 28) + 1:02d}"
        if i >= 28:
            d = f"2026-02-{(i % 28) + 1:02d}"
        if i >= 56:
            d = f"2026-03-{(i % 28) + 1:02d}"
        if i >= 84:
            d = f"2026-04-{(i % 28) + 1:02d}"
        shock = -0.03 if i % 7 == 0 else 0.01
        price = max(10.0, price * (1.0 + shock))
        row = {
            "eval_date": d,
            "mapping_target": "bull",
            "regime_hypothesis": "crisis" if i % 7 == 0 else "calm",
            "market_sasang_lens_snapshot": {
                "state_vector_sasang_softmax": {
                    "taeyang": 0.1,
                    "soyang": 0.1,
                    "taeeum": 0.1,
                    "soeum": 0.7,
                },
                "fusion_bridge": {"direction_hint": "bull", "score_hint": 0.05},
                "uncertainty": {"composite_uncertainty": 0.6},
                "veto": {"force_hold": False},
            },
            "machine_readables": {
                "direction_score": 0.08,
                "cold_proxy": 0.85,
                "heat_proxy": 0.3,
                "volatility_rarefaction_proxy": 0.7,
            },
        }
        rows.append(row)
        klines.append(f"{d},{price:.4f}")
    per_date.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    kospi.write_text("\n".join(klines) + "\n", encoding="utf-8")

    doc = lib.evaluate_mdd_safeguard_holdout(
        per_date_path=per_date,
        kospi_csv=kospi,
        holdout_days=30,
    )
    assert doc["schema"] == "ijeoma_kernel_v2_mdd_safeguard_holdout_eval_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["promotion_to_a_track_allowed"] is False
    p10 = (doc["per_arm"]["P10_kernel_v2_grid_best"]["holdout"])["n_active_days"]
    p8 = (doc["per_arm"]["P8_kernel_v2_bomyung_fuse"]["holdout"])["n_active_days"]
    assert p8 <= p10


def test_evaluate_mdd_smoke(tmp_path: Path) -> None:
    per_date = tmp_path / "per_date.jsonl"
    kospi = tmp_path / "kospi.csv"
    rows = []
    klines = ["date,close"]
    for i in range(100):
        d = f"2026-01-{i+1:02d}" if i < 31 else f"2026-02-{i-30:02d}"
        if i >= 59:
            d = f"2026-03-{i-58:02d}"
        if i >= 90:
            d = f"2026-04-{i-89:02d}"
        rows.append(
            {
                "eval_date": d,
                "mapping_target": "bull" if i % 2 == 0 else "bear",
                "regime_hypothesis": "watch",
                "market_sasang_lens_snapshot": {
                    "fusion_bridge": {"direction_hint": "bull" if i % 2 == 0 else "bear"},
                    "veto": {"force_hold": False},
                },
            }
        )
        klines.append(f"{d},{2500.0 + i}")
    per_date.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    kospi.write_text("\n".join(klines) + "\n", encoding="utf-8")

    doc = lib.evaluate_mdd_safeguard_holdout(
        per_date_path=per_date,
        kospi_csv=kospi,
        holdout_days=15,
    )
    assert "P10_kernel_v2_grid_best" in doc["per_arm"]
    assert "mdd_comparisons_vs_baseline" in doc


def test_mdd_walkforward_smoke(tmp_path: Path) -> None:
    per_date = tmp_path / "per_date.jsonl"
    kospi = tmp_path / "kospi.csv"
    rows = []
    klines = ["date,close"]
    for i in range(300):
        y, m, d = 2025, 1 + (i // 28), (i % 28) + 1
        if m > 12:
            y += (m - 1) // 12
            m = ((m - 1) % 12) + 1
        ds = f"{y:04d}-{m:02d}-{d:02d}"
        rows.append(
            {
                "eval_date": ds,
                "mapping_target": "bull" if i % 2 == 0 else "bear",
                "regime_hypothesis": "watch",
                "market_sasang_lens_snapshot": {
                    "state_vector_sasang_softmax": {
                        "taeyang": 0.3,
                        "soyang": 0.2,
                        "taeeum": 0.25,
                        "soeum": 0.25,
                    },
                    "fusion_bridge": {"direction_hint": "bull" if i % 2 == 0 else "bear"},
                    "uncertainty": {"composite_uncertainty": 0.55},
                    "veto": {"force_hold": False},
                },
                "machine_readables": {"direction_score": 0.02 if i % 2 == 0 else -0.02},
            }
        )
        klines.append(f"{ds},{2500.0 + i}")
    per_date.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    kospi.write_text("\n".join(klines) + "\n", encoding="utf-8")

    doc = lib.evaluate_mdd_safeguard_walkforward(
        per_date_path=per_date,
        kospi_csv=kospi,
        fold_holdout_days=30,
        n_folds=2,
        confirmatory_holdout_days=30,
    )
    assert doc["schema"] == "ijeoma_kernel_v2_mdd_safeguard_walkforward_eval_v1"
    assert doc["send_gate"] == "HOLD"
    assert len(doc.get("walkforward_folds") or []) >= 2
    assert "P13_kernel_v2_bomyung_grid_best" in (
        (doc.get("confirmatory_tail") or {}).get("per_arm") or {}
    )


def test_fuse_regime_calibration_smoke(tmp_path: Path) -> None:
    import scripts.bomyung_fuse_regime_calibration_lib_v1 as cal

    per_date = tmp_path / "per_date.jsonl"
    kospi = tmp_path / "kospi.csv"
    rows = []
    klines = ["date,close"]
    regimes = ["calm", "watch", "stress", "crisis"]
    for i in range(120):
        d = f"2026-01-{(i % 28) + 1:02d}"
        if i >= 28:
            d = f"2026-02-{(i % 28) + 1:02d}"
        if i >= 56:
            d = f"2026-03-{(i % 28) + 1:02d}"
        if i >= 84:
            d = f"2026-04-{(i % 28) + 1:02d}"
        regime = regimes[i % 4]
        rows.append(
            {
                "eval_date": d,
                "mapping_target": "bull",
                "regime_hypothesis": regime,
                "market_sasang_lens_snapshot": {
                    "state_vector_sasang_softmax": {
                        "taeyang": 0.1,
                        "soyang": 0.1,
                        "taeeum": 0.1,
                        "soeum": 0.7,
                    },
                    "fusion_bridge": {"direction_hint": "bull", "score_hint": 0.05},
                    "uncertainty": {"composite_uncertainty": 0.6},
                    "veto": {"force_hold": False},
                },
                "machine_readables": {
                    "direction_score": 0.08,
                    "cold_proxy": 0.85 if regime in ("crisis", "stress") else 0.4,
                    "heat_proxy": 0.3,
                    "volatility_rarefaction_proxy": 0.7 if regime in ("crisis", "stress") else 0.2,
                },
            }
        )
        klines.append(f"{d},{2500.0 + i}")
    per_date.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    kospi.write_text("\n".join(klines) + "\n", encoding="utf-8")

    doc = cal.evaluate_bomyung_fuse_regime_calibration(
        per_date_path=per_date,
        kospi_csv=kospi,
        holdout_days=30,
        fold_holdout_days=30,
        n_folds=2,
    )
    assert doc["schema"] == "bomyung_fuse_regime_calibration_v1"
    assert doc["send_gate"] == "HOLD"
    assert "fuse_contract_v1" in doc
    assert "holdout_tail" in doc
    assert "walkforward_fold_summaries" in doc
