from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_operations_lock_declaration_v1(tmp_path: Path):
    freeze = tmp_path / "freeze.json"
    out_json = tmp_path / "lock.json"
    out_md = tmp_path / "lock.md"
    freeze.write_text(
        json.dumps(
            {
                "freeze_decision": "frozen",
                "strict_profile": {"x": 1},
                "balanced_profile": {"y": 2},
            }
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_operations_lock_declaration_v1.py",
        "--freeze-vfinal-json",
        str(freeze),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_operations_lock_declaration_v1"
    assert data["lock_state"] == "locked"
    assert data["locked_profiles"]["strict"]["x"] == 1
    assert out_md.exists()

