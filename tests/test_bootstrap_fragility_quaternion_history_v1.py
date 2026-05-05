from __future__ import annotations

import json
import subprocess
import sys


def test_bootstrap_adds_quaternion_history(tmp_path) -> None:
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps({"schema": "macro_fragility_inputs_v1"}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/bootstrap_fragility_quaternion_history_v1.py", "--input", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert "quaternion_history" in doc
    assert len(doc["quaternion_history"]) >= 14
