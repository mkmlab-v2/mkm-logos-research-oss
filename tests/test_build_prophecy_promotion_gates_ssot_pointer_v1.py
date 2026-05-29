from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_prophecy_promotion_gates_ssot_pointer_v1_stdout():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_prophecy_promotion_gates_ssot_pointer_v1.py"),
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    start = proc.stdout.index("{")
    end = proc.stdout.rindex("}") + 1
    doc = json.loads(proc.stdout[start:end])
    assert doc["schema"] == "prophecy_promotion_gates_ssot_pointer_v1"
    assert doc["policy"]["ops_closure_promotion_hold"].endswith(
        "prophecy_promotion_gates_daily_shadow_v1_latest.json"
    )
    assert doc["lanes"]["daily_shadow"]["ops_closure_primary"] is True
