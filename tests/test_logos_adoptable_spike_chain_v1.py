"""Smoke: logos adoptable spike chain artifacts exist and chain exit 0."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_adoptable_spike_chain_v1.py"
COMPLETION = ROOT / "reports/logos_adoptable_spike_chain_v1_latest.json"

ARTIFACTS = [
    ROOT / "docs/final/artifacts/logos_morphology_frequency_report_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_gematria_matrix_snapshot_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_cross_ref_sample_shard_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json",
]


def test_adoptable_spike_chain_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHAIN), "--skip-studio-copy"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_adoptable_spike_artifacts_schema():
    assert COMPLETION.is_file()
    doc = json.loads(COMPLETION.read_text(encoding="utf-8"))
    assert doc.get("quality_ok") is True
    assert doc.get("schema") == "logos_adoptable_spike_chain_v1"
    for path in ARTIFACTS:
        assert path.is_file(), path
        art = json.loads(path.read_text(encoding="utf-8"))
        assert art.get("research_only") is True
        assert art.get("send_gate") == "HOLD"


def test_taxonomy_insight_cards_count():
    tax = json.loads(
        (ROOT / "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    cards = tax.get("insight_cards") or {}
    assert tax.get("preset_count", 0) >= 17
    assert len(cards) >= 17
    sample = cards.get("job_job_suffering_reason") or {}
    assert sample.get("slot") == "job_verse"
    assert sample.get("one_liner_ko")
