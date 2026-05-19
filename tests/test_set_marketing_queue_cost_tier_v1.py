"""set_marketing_queue_cost_tier_v1 — tier_15 event week queue flags."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/set_marketing_queue_cost_tier_v1.py"
EXAMPLE = ROOT / "data/marketing/marketing_content_queue_v1.example.json"


def test_tier15_event_week_sets_allow_gemini(tmp_path):
    q = tmp_path / "q.json"
    q.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--queue",
            str(q),
            "--active-tier",
            "tier_15",
            "--event-week",
            "--gemini-item",
            "compression_governance_moat_w12",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(q.read_text(encoding="utf-8"))
    assert doc["active_cost_tier"] == "tier_15"
    assert doc["tier15_event_week"]["enabled"] is True
    by_id = {i["id"]: i for i in doc["items"]}
    assert by_id["compression_governance_moat_w12"]["allow_gemini"] is True
    assert by_id["showroom_topology_observability_ko"]["allow_gemini"] is False


def test_revert_tier0(tmp_path):
    q = tmp_path / "q.json"
    q.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SCRIPT), "--queue", str(q), "--active-tier", "tier_15", "--event-week", "--gemini-item", "compression_governance_moat_w12"],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--queue", str(q), "--active-tier", "tier_0", "--clear-event-week", "--reset-gemini-flags"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    doc = json.loads(q.read_text(encoding="utf-8"))
    assert doc["active_cost_tier"] == "tier_0"
    assert "tier15_event_week" not in doc
