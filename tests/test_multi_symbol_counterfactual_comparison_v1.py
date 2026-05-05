from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_counterfactual_comparison_gate_contract(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    survivability = artifacts / "multi_symbol_walkforward_survivability_latest.json"
    cf_set = artifacts / "multi_symbol_counterfactual_set_latest.json"
    comparison = artifacts / "multi_symbol_counterfactual_comparison_latest.json"

    _write_json(
        survivability,
        {
            "metrics": [
                {"seed_symbol": "tree_of_knowledge_good_evil", "sequence_length": 5, "survivability_score": 0.8},
                {"seed_symbol": "babel_tower", "sequence_length": 4, "survivability_score": 0.7},
            ]
        },
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_multi_symbol_counterfactual_set_v1.py"),
            "--survivability-json",
            str(survivability),
            "--output-json",
            str(cf_set),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_multi_symbol_counterfactual_comparison_v1.py"),
            "--survivability-json",
            str(survivability),
            "--counterfactual-json",
            str(cf_set),
            "--output-json",
            str(comparison),
            "--min-mean-gap",
            "0.1",
        ],
        cwd=str(ROOT),
        check=True,
    )
    doc = json.loads(comparison.read_text(encoding="utf-8"))
    assert doc["schema"] == "multi_symbol_counterfactual_comparison_v1"
    assert "mean_gap_base_minus_counterfactual" in doc["metrics"]
    assert "promotion_hold" in doc["gate_eval"]

