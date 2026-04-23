from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_strict_baseline_freeze_vfinal_v1(tmp_path: Path):
    go = tmp_path / "go.json"
    promo = tmp_path / "promo.json"
    day7 = tmp_path / "day7.json"
    stab = tmp_path / "stab.json"
    delta = tmp_path / "delta.json"
    out_json = tmp_path / "vfinal.json"
    out_md = tmp_path / "vfinal.md"
    go.write_text(json.dumps({"verdict": "go"}), encoding="utf-8")
    promo.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    day7.write_text(json.dumps({"verdict": "ready"}), encoding="utf-8")
    stab.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    delta.write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_baseline_freeze_vfinal_v1.py",
        "--promotion-go-no-go-json",
        str(go),
        "--promotion-gate-json",
        str(promo),
        "--day7-checkpoint-json",
        str(day7),
        "--freeze-v2-stability-gate-json",
        str(stab),
        "--delta-governance-json",
        str(delta),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["freeze_decision"] == "frozen"
    assert data["gate_status"]["promotion_go_no_go_verdict"] == "go"
    assert out_md.exists()

