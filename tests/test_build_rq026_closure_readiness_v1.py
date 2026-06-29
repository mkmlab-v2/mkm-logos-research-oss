"""RQ-026 closure readiness gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_rq026_closure_readiness_v1.py"


def test_closure_readiness_mechanics_ok() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/rq026_closure_readiness_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc.get("mechanics_bundle_ok") is True
    close = ROOT / "docs/final/artifacts/rq026_commander_close_v1_latest.json"
    if close.is_file() and json.loads(close.read_text(encoding="utf-8")).get("rq_026_closed"):
        assert doc.get("closure_allowed") is True
    else:
        assert doc.get("closure_allowed") is False
