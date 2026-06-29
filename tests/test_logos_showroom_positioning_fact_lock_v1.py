# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_logos_showroom_positioning_fact_lock_v1.py"
SSOT = ROOT / "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json"


def test_positioning_ssot_exists() -> None:
    assert SSOT.is_file()
    doc = json.loads(SSOT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_showroom_positioning_fact_lock_v1"
    assert "logos_oracle_v6" in doc["products"]
    assert doc["products"]["magic_orb_graph_bloom"]["node_cap"] == 64


def test_positioning_guard_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
