from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_strict_baseline_freeze_v2_rollover_v1_noop(tmp_path: Path):
    v1 = tmp_path / "v1.json"
    day7 = tmp_path / "day7.json"
    out_roll = tmp_path / "roll.json"
    out_hist = tmp_path / "roll_hist.jsonl"
    v1.write_text(json.dumps({"profile": {"x": 1}, "gate_status": {"a": "pass"}}, ensure_ascii=False), encoding="utf-8")
    day7.write_text(json.dumps({"verdict": "hold"}, ensure_ascii=False), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_baseline_freeze_v2_rollover_v1.py",
        "--freeze-v1-json",
        str(v1),
        "--day7-checkpoint-json",
        str(day7),
        "--output-rollover-json",
        str(out_roll),
        "--history-jsonl",
        str(out_hist),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_roll.read_text(encoding="utf-8"))
    assert data["rollover_status"] == "noop_hold"
    hist_lines = [x for x in out_hist.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(hist_lines) == 1
    evt = json.loads(hist_lines[0])
    assert evt["rollover_status"] == "noop_hold"


def test_build_canon_singularity_strict_baseline_freeze_v2_rollover_v1_rolled(tmp_path: Path):
    v1 = tmp_path / "v1.json"
    day7 = tmp_path / "day7.json"
    health = tmp_path / "health.json"
    promo = tmp_path / "promo.json"
    bench = tmp_path / "bench.json"
    delta = tmp_path / "delta.json"
    out_roll = tmp_path / "roll.json"
    out_v2 = tmp_path / "v2.json"
    out_diff = tmp_path / "diff.json"
    out_hist = tmp_path / "roll_hist.jsonl"
    v1.write_text(
        json.dumps(
            {
                "profile": {
                    "health_max_fail_count": 0,
                    "health_min_pass_rate": 1.0,
                    "insight_delta_min_score": 0.002,
                    "delta_governance_min_apply_rate": 0.1,
                    "require_explainability_benchmark": True,
                },
                "gate_status": {"day7_checkpoint_verdict": "hold"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    day7.write_text(json.dumps({"verdict": "ready"}, ensure_ascii=False), encoding="utf-8")
    health.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    promo.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    bench.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    delta.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_baseline_freeze_v2_rollover_v1.py",
        "--freeze-v1-json",
        str(v1),
        "--day7-checkpoint-json",
        str(day7),
        "--quality-gate-policy-json",
        str(health),
        "--promotion-gate-json",
        str(promo),
        "--explainability-benchmark-gate-json",
        str(bench),
        "--delta-governance-json",
        str(delta),
        "--insight-delta-min-score",
        "0.001",
        "--delta-governance-min-apply-rate",
        "0.0",
        "--output-rollover-json",
        str(out_roll),
        "--output-v2-json",
        str(out_v2),
        "--output-diff-json",
        str(out_diff),
        "--history-jsonl",
        str(out_hist),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    roll = json.loads(out_roll.read_text(encoding="utf-8"))
    assert roll["rollover_status"] == "rolled"
    v2 = json.loads(out_v2.read_text(encoding="utf-8"))
    assert v2["schema"] == "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2"
    diff = json.loads(out_diff.read_text(encoding="utf-8"))
    assert diff["change_count"] >= 1
    hist_lines = [x for x in out_hist.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(hist_lines) == 1
    evt = json.loads(hist_lines[0])
    assert evt["rollover_status"] == "rolled"
    assert evt["freeze_decision"] in {"frozen", "hold"}

