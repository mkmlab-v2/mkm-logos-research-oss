"""Golden 40 expansion dry-run — plan-only and merge helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_golden40_expansion_dryrun_v1 import (
    _distribution,
    _golden_cases,
    _homogeneous_sasang_pool,
    _interleave_lane_batches,
    _merge_for_target,
    _percentile,
    _resolve_expansion_pool,
)


def test_percentile_and_distribution() -> None:
    vals = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert _percentile(vals, 50) == 0.3
    cases = [
        {"token_saving_rate": 0.4, "reconstruction_fidelity_jaccard": 0.88},
        {"token_saving_rate": 0.5, "reconstruction_fidelity_jaccard": 0.90},
    ]
    dist = _distribution(cases)
    assert dist["case_count"] == 2
    assert dist["token_saving_rate"]["mean"] == 0.45


def test_merge_for_target_keeps_golden_first() -> None:
    golden = [{"id": f"g{i}", "raw_text": "x"} for i in range(40)]
    pool = [{"id": f"lane__p{i}", "raw_text": "y"} for i in range(100)]
    merged = _merge_for_target(golden, pool, 60)
    assert len(merged) == 60
    assert merged[0]["id"] == "g0"
    assert merged[39]["id"] == "g39"
    assert merged[40]["id"] == "lane__p0"


def test_golden_cases_load_at_least_40() -> None:
    cases = _golden_cases()
    assert len(cases) >= 40
    assert cases[0].get("lane_id") == "golden_full_v2_40"


def test_interleave_round_robin() -> None:
    a = [{"id": "a1"}, {"id": "a2"}]
    b = [{"id": "b1"}, {"id": "b2"}, {"id": "b3"}]
    merged = _interleave_lane_batches(a, b)
    assert [r["id"] for r in merged] == ["a1", "b1", "a2", "b2", "b3"]


def test_homogeneous_pool_smaller_than_mixed_registry() -> None:
    import json

    from scripts.run_golden40_expansion_dryrun_v1 import REGISTRY

    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    homo, _ = _homogeneous_sasang_pool()
    mixed, _ = _resolve_expansion_pool("mixed_matrix", reg)
    assert len(homo) < len(mixed)
    assert len(homo) >= 50


def test_plan_only_exit_zero(tmp_path: Path, monkeypatch) -> None:
    import scripts.run_golden40_expansion_dryrun_v1 as mod

    out = tmp_path / "dryrun.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_golden40_expansion_dryrun_v1.py",
            "--target-counts",
            "40,80",
            "--plan-only",
            "--out-json",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["would_change_active"] is False
    assert doc["summary"]["promotion_recommendation"] == "HOLD"
    assert len(doc["tiers"]) == 2
    assert doc["tiers"][0]["plan_only"] is True
