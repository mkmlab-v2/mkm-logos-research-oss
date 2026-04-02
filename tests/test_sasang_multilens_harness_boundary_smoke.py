# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke — Sasang dynamics ledger JSONL vs multilens thin harness lens slot boundary
# Keywords: sasang, multilens, b-track, harness, boundary

"""Minimal boundary smoke: ledger SSOT file coexists with multilens thin harness sasang slot.

The dynamics JSONL (`data/sasang/sasang_dynamics_regime_mapping_v1.sample.jsonl`) is append/validate
workflow SSOT. The thin multilens harness (`eval_multilens_harness_v2_thin.py`) uses embedded
curated dates for `sasang_b_track` rows — it does not read this JSONL by default. This test only
locks that both layers exist and share hypothesis vocabulary overlap for CI drift detection.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_LEDGER = _ROOT / "scripts" / "sasang_dynamics_regime_mapping_ledger.py"
_THIN = _ROOT / "scripts" / "eval_multilens_harness_v2_thin.py"

_REGIME_ALLOWED = frozenset(
    {"expansion", "contraction", "phase_transition", "extreme_tail", "neutral"}
)


def _load_ledger():
    spec = importlib.util.spec_from_file_location(
        "sasang_dynamics_regime_mapping_ledger", _LEDGER
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_thin():
    spec = importlib.util.spec_from_file_location(
        "eval_multilens_harness_v2_thin", _THIN
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sasang_dynamics_sample_jsonl_validates_expected_lines() -> None:
    mod = _load_ledger()
    path = _ROOT / "data" / "sasang" / "sasang_dynamics_regime_mapping_v1.sample.jsonl"
    n = mod.validate_jsonl_file(path)
    assert n == 6


def test_multilens_thin_harness_exposes_sasang_b_track_slot() -> None:
    thin = _load_thin()
    r = thin.run_thin_harness(_ROOT, populate_default_samples=True)
    assert r.get("schema") == "multilens_eval_v2_thin_report_v1"
    lo = r["rows"][0]["lens_outputs"]
    assert "sasang_b_track" in lo
    assert lo["sasang_b_track"]["regime_hypothesis"] in _REGIME_ALLOWED


def test_ledger_regime_vocab_covers_thin_populated_hypothesis() -> None:
    """Embedded thin harness row uses a hypothesis that must remain ledger-valid."""
    thin = _load_thin()
    r = thin.run_thin_harness(_ROOT, populate_default_samples=True)
    by_date = {row["calendar_date"]: row["lens_outputs"] for row in r["rows"]}
    for d, lo in by_date.items():
        sb = lo.get("sasang_b_track")
        assert sb is not None, d
        assert sb["regime_hypothesis"] in _REGIME_ALLOWED
