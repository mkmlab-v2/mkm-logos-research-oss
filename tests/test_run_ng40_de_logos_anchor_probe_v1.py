"""Offline contract tests for ng40 DE logos anchor probe."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_ng40_de_logos_anchor_probe_v1.py"
NAV = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"


def test_dry_run_emits_schema_and_probes():
    out = ROOT / "reports/_test_ng40_de_logos_anchor_probe_v1.json"
    if out.is_file():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ng40_de_logos_anchor_probe_v1"
    assert doc["research_only"] is True
    assert doc["hypo_label"] == "[HYPO]"
    assert doc["dry_run"] is True
    assert doc["probe_count"] >= 3
    assert "auto_merge_hits_into_ng40_codec" in doc["forbidden"]
    for pr in doc["probes"]:
        assert "probe_id" in pr
        assert "query" in pr
    out.unlink(missing_ok=True)


def test_queries_from_nav_frame_count():
    from scripts.run_ng40_de_logos_anchor_probe_v1 import _queries_from_nav_frame

    nav = json.loads(NAV.read_text(encoding="utf-8-sig"))
    probes = _queries_from_nav_frame(nav)
    assert len(probes) == 5  # 3 archetype nodes + 2 modern concepts
    ids = {p["probe_id"] for p in probes}
    assert "nav:archetype:blood_covenant" in ids
    assert "concept:concept:semiconductor" in ids
