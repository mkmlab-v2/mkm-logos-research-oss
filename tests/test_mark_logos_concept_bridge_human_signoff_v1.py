# @MKM12-METADATA
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_mark_signoff_requires_ack_flag(tmp_path: Path) -> None:
    reg = {
        "schema": "logos_concept_bridge_registry_v1",
        "entries": [],
    }
    reg_path = tmp_path / "reg.json"
    reg_path.write_text(json.dumps(reg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/mark_logos_concept_bridge_human_signoff_v1.py"),
            "--registry-json",
            str(reg_path),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
