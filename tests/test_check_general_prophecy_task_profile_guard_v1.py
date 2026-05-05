from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_general_prophecy_task_profile_guard_v1.py"


def test_task_profile_guard_smoke():
    out = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_task_profile_guard_latest.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--task-name",
            "\\GeneralProphecyDailyQueueV1",
            "--required-profile",
            "ops",
            "--required-include-logos-v2",
            "true",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "general_prophecy_task_profile_guard_v1"
    assert doc["query_ok"] is True
    assert doc["decision"] in {"TASK_PROFILE_AND_LOGOS_OK", "TASK_PROFILE_OR_LOGOS_MISMATCH"}
