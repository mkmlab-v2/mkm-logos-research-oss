"""Smoke: saju_askone_verify_bundle_v1.py outputs ask-one verify shape."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_askone_verify_bundle_utc_mode() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "saju_askone_verify_bundle_v1.py"),
            "--birth-instant-utc",
            "2014-05-08T16:26:00Z",
            "--tz",
            "Asia/Seoul",
            "--male",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    doc = json.loads(proc.stdout)
    assert doc["gate_status"] in {"CONFIRMED", "REVIEW", "BLOCK"}
    assert "primary" in doc
    if doc["gate_status"] != "BLOCK":
        assert doc.get("myeongni_lite") is not None
        lite = doc["myeongni_lite"]
        assert lite.get("daewoon_current", {}).get("pillar")
