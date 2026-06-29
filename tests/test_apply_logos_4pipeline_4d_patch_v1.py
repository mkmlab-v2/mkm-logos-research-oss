# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_logos_4pipeline_4d_patch_dry_run() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "apply_logos_4pipeline_4d_patch_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["dry_run"] is True
    assert doc["applied"] == 2320
