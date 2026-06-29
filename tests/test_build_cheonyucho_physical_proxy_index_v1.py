"""Smoke: physical proxy index builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_physical_proxy_index_smoke() -> None:
    script = ROOT / "scripts" / "build_cheonyucho_physical_proxy_index_v1.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "cheonyucho_physical_proxy_index_v1"
    assert doc["proxy_count"] >= 4
    assert doc["p1_01_verdict"]["rear_index"] == "absent_nlk_confirmed"

    probe = json.loads(
        (ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json").read_text(
            encoding="utf-8-sig"
        )
    )
    p101 = next(c for c in probe["checklist"] if c["id"] == "P1-01")
    assert p101["status"] == "nl_briefing_only"
    assert probe.get("physical_anchor", {}).get("library_call_no") == "199.1-이617ㄱ"
