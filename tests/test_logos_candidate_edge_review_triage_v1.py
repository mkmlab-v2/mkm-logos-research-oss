"""Smoke: review triage + ann_lite canonical merge chain (dry/skip merge)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "scripts/run_logos_candidate_edge_review_triage_v1.py"
MERGE_CHAIN = ROOT / "scripts/run_logos_candidate_edge_ann_lite_canonical_merge_chain_v1.py"


def test_run_logos_candidate_edge_review_triage_v1_skip_refresh() -> None:
    cp = subprocess.run(
        [sys.executable, str(TRIAGE), "--skip-queue-refresh"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_candidate_edge_review_triage_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "logos_candidate_edge_review_triage_v1"
    assert doc["research_only"] is True
    assert doc["queue_stats"]["total_items"] >= 1


def test_ann_lite_canonical_merge_chain_skip_merge() -> None:
    pending = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_ann_lite_v1.jsonl"
    if not pending.is_file():
        return
    cp = subprocess.run(
        [
            sys.executable,
            str(MERGE_CHAIN),
            "--skip-canonical-merge",
            "--skip-verify",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (
            ROOT / "docs/final/artifacts/logos_candidate_edge_ann_lite_canonical_merge_chain_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert doc["lane_id"] == "ann_lite"
    assert doc["canonical_merge_ran"] is False
