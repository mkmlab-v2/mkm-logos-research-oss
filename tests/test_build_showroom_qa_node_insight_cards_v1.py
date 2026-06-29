"""Insight cards builder smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_showroom_qa_node_insight_cards_v1.py"
JOB_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_job_reading_pack_slice_v1.json"
)


DEFAULT_PRESETS = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)


def test_build_insight_cards_has_job_anchor(tmp_path: Path) -> None:
    out = tmp_path / "cards.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--job-slice-json",
            str(JOB_SLICE),
            "--out-mvp",
            str(out),
            "--out-artifact",
            str(tmp_path / "mirror.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_qa_node_insight_cards_v1"
    cards = doc.get("cards") or {}
    assert "showroom_job_verse::Job.1.6" in cards
    assert cards["showroom_job_verse::Job.1.6"].get("pack_url")


def test_build_insight_cards_has_psalm_anchor(tmp_path: Path) -> None:
    out = tmp_path / "cards.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--job-slice-json",
            str(JOB_SLICE),
            "--presets-json",
            str(DEFAULT_PRESETS),
            "--out-mvp",
            str(out),
            "--out-artifact",
            str(tmp_path / "mirror.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    cards = doc.get("cards") or {}
    assert "showroom_psalm_verse::Ps.27.14" in cards
    assert cards["showroom_psalm_verse::Ps.27.14"].get("kind") == "psalm_verse"
    assert "theme::hope_endurance_psalm" in cards
