# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_high_l2_dissection_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_4d_high_l2_dissection_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads((ROOT / "reports/logos_4d_high_l2_dissection_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert doc["count"] == 28


def test_gp_june_preflight_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_general_prophecy_logos_june_resolve_preflight_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads((ROOT / "reports/general_prophecy_logos_june_resolve_preflight_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert len(doc["questions"]) == 4
    assert all(not q.get("resolve_ready_now") for q in doc["questions"])
