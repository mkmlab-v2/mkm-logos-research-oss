"""M26: Track C ops dashboard inter_agent_rq019 merge + regression chain m25 gates."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trackc_dashboard_inter_agent_rq019():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(
        (ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json").read_text(encoding="utf-8")
    )
    ia = (doc.get("trackc") or {}).get("inter_agent_rq019") or {}
    assert ia.get("role") == "inter_agent_rq019_research_slice_v1"
    assert ia.get("research_only") is True
    assert ia.get("state") in ("OK", "DEGRADED")
    assert "rq_019" in ia
    assert "language_dev_m12_m25_ready" in ia


def test_rq019_regression_chain_quick_m25():
    from scripts.run_mkm_inter_agent_rq019_regression_chain_v1 import run_chain

    doc = run_chain(skip_pytest=True, quick=True)
    assert doc.get("ok")
    flags = doc.get("encoding_status_flags") or {}
    assert flags.get("m12_m25_ready") is True


def test_trackc_slice_dashboard_fields():
    from scripts.build_mkm_inter_agent_trackc_rq019_slice_v1 import build_slice, dashboard_fields

    fields = dashboard_fields(build_slice())
    assert fields.get("role") == "inter_agent_rq019_research_slice_v1"
    assert fields.get("research_only") is True
