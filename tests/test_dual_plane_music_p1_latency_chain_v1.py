from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dual_plane_music_p1_harmonic_crosswalk_v1.json"
CHAIN = ROOT / "scripts/run_dual_plane_music_p1_latency_chain_v1.py"
EXPORT = ROOT / "scripts/build_investor_deck_ko_export_md_v1.py"


def test_latency_chain_symbolic_ok_skip_ollama(tmp_path):
    out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--fixture",
            str(FIXTURE),
            "--skip-ollama",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["symbolic_plane"]["metrics"]["post_project_illegal_rate"] == 0.0
    assert doc["integrity"]["collapsed_combined_score"] is None


def test_investor_deck_export_md(tmp_path):
    out_md = tmp_path / "deck.md"
    proc = subprocess.run(
        [sys.executable, str(EXPORT), "--out", str(out_md)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out_md.read_text(encoding="utf-8")
    assert "Slide 09" in text
    assert "Slide 10" in text
    assert "FaithTech" in text
