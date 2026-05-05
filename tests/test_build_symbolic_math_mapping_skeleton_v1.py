from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_symbolic_math_mapping_skeleton_v1.py"


def test_build_symbolic_math_mapping_skeleton_v1(tmp_path: Path) -> None:
    out = tmp_path / "symbolic_math_mapping_skeleton.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--w-dist",
            "0.65",
            "--w-consistency",
            "0.35",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "symbolic_math_mapping_skeleton_v1"
    assert doc["track"] == "B_TRACK"
    assert doc["space_contract"]["vector4d_axes"] == ["S", "L", "K", "M"]
    assert doc["quaternion_contract"]["format"] == "wxyz"
    assert doc["loss_function_contract"]["weights"]["w_dist"] == 0.65
    assert doc["loss_function_contract"]["weights"]["w_consistency"] == 0.35
