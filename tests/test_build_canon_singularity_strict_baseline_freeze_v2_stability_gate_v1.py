from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_strict_baseline_freeze_v2_stability_gate_v1_pass(tmp_path: Path):
    hist = tmp_path / "roll_hist.jsonl"
    out_json = tmp_path / "gate.json"
    out_md = tmp_path / "gate.md"
    rows = [
        {"freeze_decision": "frozen", "rollover_status": "rolled"},
        {"freeze_decision": "frozen", "rollover_status": "rolled"},
        {"freeze_decision": "hold", "rollover_status": "rolled"},
        {"freeze_decision": "frozen", "rollover_status": "rolled"},
        {"freeze_decision": "frozen", "rollover_status": "rolled"},
    ]
    hist.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_baseline_freeze_v2_stability_gate_v1.py",
        "--history-jsonl",
        str(hist),
        "--window",
        "5",
        "--min-window-size",
        "5",
        "--min-frozen-rate",
        "0.8",
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    assert data["metrics"]["frozen_rate"] == 0.8
    assert out_md.exists()


def test_build_canon_singularity_strict_baseline_freeze_v2_stability_gate_v1_fail_small_window(tmp_path: Path):
    hist = tmp_path / "roll_hist.jsonl"
    out_json = tmp_path / "gate.json"
    rows = [
        {"freeze_decision": "frozen", "rollover_status": "rolled"},
        {"freeze_decision": "hold", "rollover_status": "rolled"},
    ]
    hist.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_baseline_freeze_v2_stability_gate_v1.py",
        "--history-jsonl",
        str(hist),
        "--window",
        "7",
        "--min-window-size",
        "5",
        "--min-frozen-rate",
        "0.8",
        "--output-json",
        str(out_json),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "fail"
    assert data["checks"]["window_size_ok"] is False

