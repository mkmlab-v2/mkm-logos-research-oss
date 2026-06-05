# -*- coding: utf-8 -*-
"""Smoke: logos topic 4D resonance spike (B-track, no Track A).

Contract-only: validates schema, research_only, and top_k shape.
Does NOT assert organic seed∩top_k (0/6 is expected under current bridge).
CI policy: docs/final/artifacts/logos_4d_topic_spike_ci_policy_v1.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_topic_4d_resonance_spike_smoke() -> None:
    script = ROOT / "scripts" / "build_logos_topic_4d_resonance_spike_v1.py"
    fixture = ROOT / "tests" / "fixtures" / "logos_topic_4d_resonance_graphrag_2026_v1.json"
    out = ROOT / "reports" / "tmp_logos_topic_4d_resonance_spike_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(script),
            "--topics-json",
            str(fixture),
            "--max-verses",
            "800",
            "--top-k",
            "3",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_topic_4d_resonance_spike_v1"
    assert doc.get("research_only") is True
    assert doc.get("non_gating") is True
    assert doc["fact_lock"]["compression_track_a_touch"] is False
    assert len(doc.get("topics") or []) == 7
    for topic in doc["topics"]:
        assert len(topic.get("top_k") or []) <= 3
        assert topic.get("graphrag_ref")
    # Organic promotion gate intentionally not checked (see CI policy).
    _ = sum(1 for t in doc["topics"] if t.get("seed_in_top_k"))
