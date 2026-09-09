"""Tests for MKM_CORE_MAP v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
MAP = ROOT / "docs/final/artifacts/mkm_core_coordinate_map_v1_latest.json"
MDC = ROOT / ".cursor/rules/mkm-core-coordinate-map-v1.mdc"
CHK = ROOT / "docs/final/artifacts/mkm_core_coordinate_map_check_v1_latest.json"


def test_build_and_check_strict():
    r = subprocess.run(
        [PY, "scripts/check_mkm_core_coordinate_map_v1.py", "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
    assert MAP.is_file()
    assert MDC.is_file()
    doc = json.loads(MAP.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "mkm_core_coordinate_map_v1"
    assert doc["ok"] is True
    assert doc["inject_policy"]["always_apply_expansion"] is False
    assert len(doc["anchor_lines"]) >= 3
    assert doc["coord_count"] >= 10
    text = MDC.read_text(encoding="utf-8")
    assert "alwaysApply: false" in text
    assert "하드 제약" in text or "격벽" in text
    chk = json.loads(CHK.read_text(encoding="utf-8-sig"))
    assert chk["ok"] is True
