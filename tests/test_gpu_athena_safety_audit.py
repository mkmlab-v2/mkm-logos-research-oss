from __future__ import annotations

import json
from pathlib import Path


def test_gpu_sim_to_edge_sweep_outputs_topk(tmp_path: Path) -> None:
    import scripts.run_gpu_sim_to_edge_sweep_v1 as mod

    out = tmp_path / "sweep.json"
    rc = mod.main(
        [
            "--target-p99-ms",
            "40",
            "--model-sizes-m",
            "40,60",
            "--batch-sizes",
            "4,8",
            "--top-k",
            "2",
            "--output-json",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "gpu_sim_to_edge_sweep_v1"
    assert doc["summary"]["selected_count"] == 2
    assert len(doc["selected_candidates"]) == 2
    assert doc["constraints"]["final_promotion_requires_target_board_measurement"] is True


def test_athena_safety_judge_generates_requested_sample_count(tmp_path: Path) -> None:
    import scripts.build_athena_safety_judge_v1 as mod

    out = tmp_path / "judge.json"
    rc = mod.main(["--sample-count", "120", "--seed", "7", "--output-json", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "athena_safety_judge_v1"
    assert doc["summary"]["total"] == 120
    assert len(doc["samples"]) == 120
    labels = {row["judge_label"] for row in doc["samples"]}
    assert labels.issubset({"GO", "WATCH", "HOLD"})
