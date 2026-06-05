from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json"


def test_crosswalk_builds_with_election_primary():
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_kospi_june2026_logos_anchor_crosswalk_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "kospi_june2026_logos_anchor_crosswalk_v1"
    assert doc.get("research_only") is True
    anchors = doc.get("anchors") or []
    assert len(anchors) >= 2
    topic_ids = {a["topic_id"] for a in anchors}
    assert "election_20260603" in topic_ids
    assert "regime_watch_lehman_shadow" in topic_ids
    assert "risk_off_overnight" in topic_ids
    assert anchors[0].get("router_overlap")
