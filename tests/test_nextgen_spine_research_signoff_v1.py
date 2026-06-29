"""[HYPO] Spine research signoff + headline exclusion from promotion packet."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_record_signoff_and_headline_exclusion():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/record_nextgen_spine_research_signoff_v1.py")],
        cwd=str(ROOT),
        check=True,
        timeout=30,
    )
    sign = json.loads(
        (
            ROOT / "reports/ng40_spine_binary_research_signoff_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert sign["evidence_arms"]["longform"]["excluded_from_headline_selection"] is True

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py"),
        ],
        cwd=str(ROOT),
        check=True,
        timeout=60,
    )
    pkt = json.loads(
        (
            ROOT / "reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    excluded = set(pkt["headline_selection_policy"]["excluded_arm_ids"])
    assert "ng40_spine_binary_billable_longform_v1" in excluded
    assert pkt.get("selected_arm") != "ng40_spine_binary_billable_longform_v1"
    hi = pkt.get("evidence_only_highlight") or {}
    assert hi.get("excluded_from_headline_selection") is True

    sched = json.loads(
        (ROOT / "reports/bls_unemployment_watch_schedule_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert sched["release_window_local_date"] == "2026-06-06"
