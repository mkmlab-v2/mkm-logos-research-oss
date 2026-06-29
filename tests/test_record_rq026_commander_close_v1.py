"""RQ-026 commander close (human gate)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/record_rq026_commander_close_v1.py"


def test_record_rq026_commander_close_schema(tmp_path: Path) -> None:
    out = tmp_path / "close.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--close-reference",
            "COMMANDER-RQ026-CLOSE-TEST",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "rq026_commander_close_v1"
    assert doc.get("rq_026_closed") is True
    assert doc.get("rq_026_status") == "CLOSED"
    assert doc.get("research_only") is True
    not_promoted = doc.get("explicit_not_promoted") or []
    assert "NG-40 codec merge" in not_promoted
    assert "Track A ACTIVE report" in not_promoted
