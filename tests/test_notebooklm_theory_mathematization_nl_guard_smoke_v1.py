"""Static NL guard smoke for theory mathematization pack + canon."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_notebooklm_theory_mathematization_nl_guard_smoke_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/notebooklm_theory_mathematization_nl_guard_smoke_v1_latest.json"
STATIC_ARTIFACT = ROOT / "docs/final/artifacts/notebooklm_theory_mathematization_nl_guard_smoke_static_v1_latest.json"


def test_nl_guard_smoke_static_skip_mcp_exit0():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-mcp"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(STATIC_ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "notebooklm_theory_mathematization_nl_guard_smoke_v1"
    assert doc["aggregate"]["static_ok"] is True
    assert doc["mcp_guard"]["skipped"] is True


def test_build_report_static_guard_unit():
    sys.path.insert(0, str(ROOT))
    from scripts.run_notebooklm_theory_mathematization_nl_guard_smoke_v1 import (  # noqa: E402
        CHECKLIST,
        build_report,
    )

    checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    doc = build_report(skip_mcp=True, checklist=checklist)
    assert doc["static_guard"]["static_ok"] is True
    assert doc["aggregate"]["all_ok"] is True
