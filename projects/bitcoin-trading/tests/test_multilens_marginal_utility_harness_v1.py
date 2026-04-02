"""Regression tests for scripts/eval_multilens_marginal_utility_v1.py (harness V1)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_WS = Path(__file__).resolve().parents[3]
_SCR = _WS / "scripts" / "eval_multilens_marginal_utility_v1.py"

if str(_WS / "projects" / "bitcoin-trading") not in sys.path:
    sys.path.insert(0, str(_WS / "projects" / "bitcoin-trading"))


def _load_harness():
    spec = importlib.util.spec_from_file_location("eval_multilens_marginal_utility_v1", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


harness = _load_harness()


@pytest.mark.regime_integrity
def test_harness_builtin_rows_myeongni_and_bible_deltas() -> None:
    """Deterministic caps from regime_fusion_policy SSOT + fixed stress inputs."""
    report = harness.run_marginal_utility_harness(_WS, scenarios=None)
    assert report["schema"] == "multilens_marginal_utility_report_v1"
    rows = {r["id"]: r for r in report["rows"]}

    mye = rows["builtin_myeongni_clamp_row"]
    assert mye["full"]["risk_multiplier_cap"] == pytest.approx(0.85, abs=1e-9)
    nm = mye["ablations"]["no_myeongni_state"]["deltas_vs_full"]["risk_cap"]
    assert nm == pytest.approx(0.07, abs=1e-9)

    bib = rows["builtin_bible_stress_row"]
    assert bib["full"]["risk_multiplier_cap"] == pytest.approx(0.92, abs=1e-9)
    nb = bib["ablations"]["no_bible_stress"]["deltas_vs_full"]["risk_cap"]
    assert nb == pytest.approx(0.08, abs=1e-9)

    assert report["summary"]["row_count"] == 2
    assert report["summary"]["mean_abs_risk_cap_delta"]["no_logos"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.regime_integrity
def test_harness_custom_grid_loads() -> None:
    one = [
        {
            "id": "single",
            "as_of": "2026-03-29T12:00:00",
            "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
            "psi_score": 0.5,
            "bible_risk_score": 0.5,
            "context_metrics": {"fear_greed_index": 0.5},
            "state_id": 7,
        }
    ]
    report = harness.run_marginal_utility_harness(_WS, scenarios=one)
    assert len(report["rows"]) == 1
    assert report["rows"][0]["id"] == "single"
