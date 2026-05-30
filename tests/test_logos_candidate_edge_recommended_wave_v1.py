"""Smoke: covenant review pack + recommended wave netnew builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_covenant_convergence_review_pack_v1() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_covenant_convergence_review_pack_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "reports/logos_covenant_convergence_review_pack_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["schema"] == "logos_covenant_convergence_review_pack_v1"
    assert len(doc.get("items") or []) >= 1
    assert (ROOT / "reports/logos_covenant_convergence_review_pack_v1_latest.md").is_file()


def test_recommended_wave_skip_offline_batch() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_candidate_edge_recommended_wave_v1.py"),
            "--skip-triage",
            "--skip-ann-lite-merge",
            "--skip-offline-4d-batch",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
