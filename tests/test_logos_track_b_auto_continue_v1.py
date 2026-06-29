from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_macula_discovery_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/discover_macula_tsv_dir_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/macula_tsv_dir_discovery_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("schema") == "macula_tsv_dir_discovery_v1"


def test_ms_paste_refresh() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/refresh_ms_proposal_paste_artifacts_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/ms_proposal_paste_ready_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("paste_ready") is True
    assert doc["artifacts"]["one_pager_ko"]["ready"] is True


def test_auto_continue_skip_ollama() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_auto_continue_v1.py"),
            "--skip-phase-l",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/logos_track_b_auto_continue_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("ms_paste_ready") is True
