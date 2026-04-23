from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_strict_baseline_freeze_generation_diff_vfinal_v1(tmp_path: Path):
    v1 = tmp_path / "v1.json"
    v2 = tmp_path / "v2.json"
    vf = tmp_path / "vf.json"
    out_json = tmp_path / "diff.json"
    out_md = tmp_path / "diff.md"
    v1.write_text(json.dumps({"freeze_decision": "frozen", "gate_status": {"a": "x"}, "profile": {"p": 1}}), encoding="utf-8")
    v2.write_text(json.dumps({"freeze_decision": "hold", "gate_status": {"a": "y"}, "profile": {"p": 1}}), encoding="utf-8")
    vf.write_text(
        json.dumps({"freeze_decision": "frozen", "gate_status": {"a": "y"}, "strict_profile": {"p": 2}, "balanced_profile": {"q": 3}}),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_strict_baseline_freeze_generation_diff_vfinal_v1.py",
        "--freeze-v1-json",
        str(v1),
        "--freeze-v2-json",
        str(v2),
        "--freeze-vfinal-json",
        str(vf),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1"
    assert data["total_change_count"] >= 1
    assert out_md.exists()

