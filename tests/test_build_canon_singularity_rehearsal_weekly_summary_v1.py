from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_rehearsal_weekly_summary_v1(tmp_path: Path):
    hist = tmp_path / "hist.jsonl"
    freeze_gate = tmp_path / "freeze_gate.json"
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    rows = [
        {
            "task": {"last_result": "0"},
            "promotion_gate": {"status": "pass"},
            "delta_governance_gate": {"status": "pass"},
            "delta_cutoff_autotune": {"status": "hold", "apply_reason": "kept_current_insufficient_signal"},
        },
        {
            "task": {"last_result": "1"},
            "promotion_gate": {"status": "fail"},
            "delta_governance_gate": {"status": "fail"},
            "delta_cutoff_autotune": {"status": "applied", "apply_reason": "applied_bounded"},
        },
        {
            "task": {"last_result": "0"},
            "promotion_gate": {"status": "pass"},
            "delta_governance_gate": {"status": "pass"},
            "delta_cutoff_autotune": {"status": "hold", "apply_reason": "kept_current_insufficient_signal"},
        },
    ]
    hist.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
    freeze_gate.write_text(
        json.dumps({"status": "pass", "metrics": {"window_size": 7, "frozen_rate": 0.857143}}, ensure_ascii=False),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_rehearsal_weekly_summary_v1.py",
        "--history-jsonl",
        str(hist),
        "--freeze-v2-stability-gate-json",
        str(freeze_gate),
        "--window",
        "3",
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_rehearsal_weekly_summary_v1"
    assert data["metrics"]["window_size"] == 3
    assert data["metrics"]["task_success_count"] == 2
    assert data["metrics"]["autotune_applied_count"] == 1
    assert data["ratios"]["governance_pass_rate"] == 0.666667
    assert data["freeze_v2_stability_gate"]["status"] == "pass"
    assert data["freeze_v2_stability_gate"]["frozen_rate"] == 0.857143
    assert out_md.exists()

