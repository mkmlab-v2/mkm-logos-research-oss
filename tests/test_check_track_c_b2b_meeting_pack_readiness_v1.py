"""Readiness gate for Track C B2B meeting pack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_meeting_pack_readiness_after_build() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_track_c_b2b_meeting_pack_v1.py"), "--skip-commander"],
        cwd=ROOT,
        check=True,
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_track_c_b2b_meeting_pack_readiness_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("ready_for_internal_meeting") is True
    assert doc.get("ready_for_external_send") is False
