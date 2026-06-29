from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_lora_tranche2_multipack_human_approval_v1_dry_run() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "apply_lora_tranche2_multipack_human_approval_v1.py"),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(cp.stdout)
    assert doc["signoff"]["schema"] == "lora_tranche2_multipack_human_signoff_v1"
    assert doc["go_no_go"]["track_a_promotion"] is False
