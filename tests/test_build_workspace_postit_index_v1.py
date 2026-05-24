"""Regression tests for workspace post-it path heuristics."""

from __future__ import annotations

from pathlib import Path

from scripts.build_workspace_postit_index_v1 import infer_track_rel


def test_infer_track_btrack_and_research() -> None:
    assert infer_track_rel("reports/constitution/btrack_pilot/foo.json") == "B"
    assert infer_track_rel("docs/research/RESEARCH_OPEN_QUESTIONS_V1.md") == "B"


def test_infer_track_governance_and_trading_ops() -> None:
    assert (
        infer_track_rel("docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md")
        == "A"
    )
    assert (
        infer_track_rel("projects/bitcoin-trading/ops/windows-rehearsal/foo.ps1")
        == "A"
    )


def test_infer_track_scripts_split() -> None:
    assert infer_track_rel("scripts/run_btrack_daily_hypothesis_chain.ps1") == "B"
    assert infer_track_rel("scripts/run_fact_lock_bundle.ps1") == "A"
    assert infer_track_rel("scripts/build_workspace_postit_index_v1.py") == "A"


def test_infer_track_docs_final_not_unknown_on_relative_path() -> None:
    assert infer_track_rel("docs/final/artifacts/foo_latest.json") == "A"


def test_infer_track_scripts_default_operational() -> None:
    assert infer_track_rel("scripts/core/foo.py") == "A"
    assert infer_track_rel("scripts/experimental/bar.py") == "B"
