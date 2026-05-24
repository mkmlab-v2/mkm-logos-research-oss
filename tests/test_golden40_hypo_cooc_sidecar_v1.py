"""Dryrun --hypo-cooc-sidecar metadata attachment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_hypo_cooc_sidecar_plan_only(tmp_path: Path, monkeypatch) -> None:
    cooc = tmp_path / "cooc.json"
    cooc.write_text(
        json.dumps({"schema": "other_cooc_cartesian_routing_poc_v2", "proceed_to_bench_hook": True}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "dryrun.json"
    import scripts.run_golden40_expansion_dryrun_v1 as mod

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_golden40_expansion_dryrun_v1.py",
            "--target-counts",
            "40",
            "--plan-only",
            "--pool-mode",
            "golden_core_only",
            "--out-json",
            str(out),
            "--hypo-cooc-sidecar",
            str(cooc),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["hypo_cooc_sidecar"]["snapshot"]["schema"] == "other_cooc_cartesian_routing_poc_v2"
