# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pending_encoder_batch_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_logos_4d_pending_encoder_batch_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    meta = json.loads((ROOT / "reports/logos_4d_encoder_reencode_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert meta["counts"]["encoded"] == 41
    assert meta["counts"]["still_fallback_after_encode"] == 0
