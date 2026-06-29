"""GraphRAG sidebar toggle for KOSPI lens ablation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_graphrag_sidebar_pack_policy() -> None:
    from scripts.kospi_lens_ablation_graphrag_sidebar_v1 import (
        SIDEBAR_POLICY_V1,
        build_graphrag_sidebar_pack,
    )

    pack = build_graphrag_sidebar_pack(enabled=True)
    assert pack["policy"]["prophecy_vote"] == "none"
    assert pack["policy"]["wires_to_scoring_core"] is False
    assert SIDEBAR_POLICY_V1["send_gate"] == "HOLD"
    assert "token_budget_proxy" in pack


def test_scoring_invariant_compare() -> None:
    from scripts.kospi_lens_ablation_graphrag_sidebar_v1 import compare_scoring_invariant

    base = {
        "arms": [
            {"arm_id": "lens3_runtime", "metrics": {"soft_hit_rate": 0.6, "directional_hit_rate": 0.65}},
        ],
        "four_ai_overlay_uplift_pp_vs_lens3_runtime": 5.0,
    }
    same = json.loads(json.dumps(base))
    inv = compare_scoring_invariant(base, same)
    assert inv["scoring_invariant"] is True
    assert inv["per_arm"][0]["soft_delta_pp"] == 0.0


def test_ablation_graphrag_compare_mode_cli() -> None:
    import scripts.run_kospi_lens_ablation_backtest_v1 as mod

    rc = mod.main(
        [
            "--date-from",
            "2026-04-01",
            "--date-to",
            "2026-05-15",
            "--graphrag-sidebar",
            "compare",
            "--output",
            str(ROOT / "reports/kospi_lens_ablation_graphrag_toggle_smoke_v1.json"),
        ]
    )
    assert rc == 0
    out = ROOT / "reports/kospi_lens_ablation_graphrag_toggle_smoke_v1.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    gr = doc["graphrag_ablation"]
    assert gr["mode"] == "compare"
    assert gr["wires_to_scoring_core"] is False
    assert gr["scoring_invariant_check"]["scoring_invariant"] is True
