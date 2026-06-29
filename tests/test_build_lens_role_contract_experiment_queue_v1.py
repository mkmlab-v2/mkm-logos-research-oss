"""B-layer role-contract fail analysis and experiment queue."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_myeongni_flat_grid_root_cause() -> None:
    from scripts.build_lens_role_contract_experiment_queue_v1 import _myeongni_fail_analysis

    grid = {
        "contract_horizon": "mid_10d",
        "contract_is_best": False,
        "contract_soft_hit_rate": 0.4999,
        "best_horizon": "mid_5d",
        "best_soft_hit_rate": 0.5001,
        "soft_delta_best_minus_contract": 0.0002,
        "contract_horizon_rank": 3,
        "ranked_by_soft_hit_rate": ["mid_5d", "mid_15d", "mid_10d"],
        "rate_by_horizon": {
            "mid_5d": {"soft_hit_rate": 0.5001},
            "mid_10d": {"soft_hit_rate": 0.4999},
            "mid_15d": {"soft_hit_rate": 0.5001},
        },
    }
    out = _myeongni_fail_analysis(grid)
    assert out["root_cause_id"] == "flat_coin_flip_grid"
    assert out["contract_is_best"] is False


def test_logos_causal_vs_snapshot_root_cause() -> None:
    from scripts.build_lens_role_contract_experiment_queue_v1 import _logos_fail_analysis

    v1 = {
        "per_lens": {
            "logos": {
                "matched_soft_hit_rate": 0.4363,
                "alignment_pass": False,
            }
        }
    }
    logos_eval = {
        "best_variant_by_macro_soft": "logos_macro_risk_causal",
        "rate_matrix": {},
        "macro_risk_coverage": {
            "operational_causal_rate": 0.0011,
            "research_backfill_rate": 0.9989,
        },
        "per_variant": {
            "logos_macro_risk_causal": {
                "matched_soft_hit_rate": 0.8432,
                "macro_alignment_pass_effective": True,
            }
        },
    }
    out = _logos_fail_analysis(v1, logos_eval)
    assert out["root_cause_id"] == "eval_path_global_snapshot_not_causal"
    assert out["best_variant_macro_21d_soft"] == 0.8432


def test_build_queue_from_disk() -> None:
    import subprocess
    import sys

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_role_contract_experiment_queue_v1.py"),
            "--merge-hitl-queue",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = ROOT / "docs/final/artifacts/lens_role_contract_experiment_queue_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_role_contract_experiment_queue_v1"
    assert doc["n_experiments"] >= 2
    assert len(doc["b_layer_summary_table"]) == 3
    assert doc["fail_analysis"]["myeongni"]["root_cause_id"] == "flat_coin_flip_grid"
