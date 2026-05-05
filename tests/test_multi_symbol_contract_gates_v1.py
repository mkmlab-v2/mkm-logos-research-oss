from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_multi_symbol_walkforward_survivability_contract(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    multi_symbol = artifacts / "multi_symbol_resonance_4d_latest.json"
    selector = artifacts / "multi_symbol_candidate_selector_latest.json"
    out = artifacts / "multi_symbol_walkforward_survivability_latest.json"

    _write_json(
        multi_symbol,
        {
            "symbols": [
                {"seed_symbol": "tree_of_knowledge_good_evil", "sequence_length": 5, "coupling_strength": 0.77, "resonance_score": 0.70},
                {"seed_symbol": "babel_tower", "sequence_length": 4, "coupling_strength": 0.70, "resonance_score": 0.63},
            ]
        },
    )
    _write_json(
        selector,
        {
            "selected": [
                {"seed_symbol": "tree_of_knowledge_good_evil"},
            ]
        },
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_multi_symbol_walkforward_survivability_v1.py"),
            "--multi-symbol-json",
            str(multi_symbol),
            "--selector-json",
            str(selector),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "multi_symbol_walkforward_survivability_v1"
    assert isinstance(doc.get("metrics"), list) and len(doc["metrics"]) == 2
    assert "top_symbol_by_survivability" in doc["summary"]


def test_multi_symbol_top_drift_gate_contract(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    survivability = artifacts / "multi_symbol_walkforward_survivability_latest.json"
    history = artifacts / "multi_symbol_top_drift_history_latest.jsonl"
    out = artifacts / "multi_symbol_top_drift_alert_latest.json"

    _write_json(
        survivability,
        {
            "summary": {"top_symbol_by_survivability": "tree_of_knowledge_good_evil"},
        },
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "alert_multi_symbol_top_drift_gate_v1.py"),
            "--survivability-json",
            str(survivability),
            "--history-jsonl",
            str(history),
            "--output-json",
            str(out),
            "--window-size",
            "5",
            "--max-switches",
            "1",
        ],
        cwd=str(ROOT),
        check=True,
    )

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "multi_symbol_top_drift_alert_v1"
    assert "gate_eval" in doc and "promotion_hold" in doc["gate_eval"]
    assert history.is_file()


def test_multi_symbol_negative_control_gate_contract(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    survivability = artifacts / "multi_symbol_walkforward_survivability_latest.json"
    negative = artifacts / "multi_symbol_negative_control_latest.json"
    gate = artifacts / "multi_symbol_negative_control_gate_latest.json"

    _write_json(
        survivability,
        {
            "metrics": [
                {"seed_symbol": "tree_of_knowledge_good_evil", "sequence_length": 5, "survivability_score": 0.80},
                {"seed_symbol": "babel_tower", "sequence_length": 4, "survivability_score": 0.74},
            ]
        },
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_multi_symbol_negative_control_v1.py"),
            "--survivability-json",
            str(survivability),
            "--output-json",
            str(negative),
        ],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "alert_multi_symbol_negative_control_gate_v1.py"),
            "--negative-control-json",
            str(negative),
            "--min-mean-uplift",
            "0.05",
            "--output-json",
            str(gate),
        ],
        cwd=str(ROOT),
        check=True,
    )

    neg = json.loads(negative.read_text(encoding="utf-8"))
    gate_doc = json.loads(gate.read_text(encoding="utf-8"))
    assert neg["schema"] == "multi_symbol_negative_control_v1"
    assert gate_doc["schema"] == "multi_symbol_negative_control_gate_v1"
    assert "mean_uplift_over_control" in gate_doc["metrics"]

