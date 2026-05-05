from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_qa_overlay_includes_counterfactual_fields(tmp_path: Path) -> None:
    artifacts = tmp_path / "docs" / "final" / "artifacts"
    qa = artifacts / "two_track_qa_pack_latest.json"
    selector = artifacts / "multi_symbol_candidate_selector_latest.json"
    fail_gate = artifacts / "two_track_fail_boundary_gate_latest.json"
    falsification = artifacts / "two_track_falsification_suite_latest.json"
    ablation = artifacts / "gematria_4d_ablation_latest.json"
    counterfactual = artifacts / "multi_symbol_counterfactual_comparison_latest.json"

    _write_json(
        qa,
        {
            "audience_qna": [
                {
                    "audience": "investor",
                    "items": [
                        {"question_id": "q3", "q": "q3", "a": "a3", "evidence": {}},
                        {"question_id": "q4", "q": "q4", "a": "a4", "evidence": {}},
                    ],
                }
            ]
        },
    )
    _write_json(selector, {"selected_count": 2, "selected": [{"seed_symbol": "tree"}, {"seed_symbol": "babel"}]})
    _write_json(fail_gate, {"gate_eval": {"pass": True, "should_trade": True, "rollback": False, "reasons": []}})
    _write_json(
        falsification,
        {"checks": [{"id": "F3", "detail": {"survivor_count": 5}}, {"id": "F4", "detail": {"shift_score": 0.8, "ci_low_defense_contrib": 0.6}}]},
    )
    _write_json(
        ablation,
        {"snapshot": {"score_with_4d": 0.7, "score_without_4d": 0.65, "delta_with_minus_without": 0.05}},
    )
    _write_json(
        counterfactual,
        {"metrics": {"mean_gap_base_minus_counterfactual": 0.3}, "gate_eval": {"pass": True, "should_alert": False, "promotion_hold": False}},
    )

    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "enrich_two_track_qa_with_symbol_evidence_v1.py"),
            "--qa-json",
            str(qa),
            "--selector-json",
            str(selector),
            "--fail-boundary-gate-json",
            str(fail_gate),
            "--falsification-json",
            str(falsification),
            "--gematria-ablation-json",
            str(ablation),
            "--counterfactual-comparison-json",
            str(counterfactual),
            "--output-json",
            str(qa),
        ],
        cwd=str(ROOT),
        check=True,
    )

    doc = json.loads(qa.read_text(encoding="utf-8"))
    items = doc["audience_qna"][0]["items"]
    q3 = items[0]["evidence"]["metric_value"]
    q4 = items[1]["evidence"]["metric_value"]
    assert "counterfactual_mean_gap" in q3
    assert "counterfactual_gate_pass" in q3
    assert "counterfactual_should_alert" in q4
    assert "counterfactual_promotion_hold" in q4

