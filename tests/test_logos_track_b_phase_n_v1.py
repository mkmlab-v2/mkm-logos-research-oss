from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_cross_theme_bridge() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_cross_theme_invariant_bridge_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("summary", {}).get("shared_hub_count", 0) >= 0


def test_phase_n_skip_ollama() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_phase_n_v1.py"),
            "--skip-ollama",
            "--max-insight-units",
            "6",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    phase_n = json.loads((_ROOT / "reports/logos_track_b_phase_n_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_n.get("ok") is True
    assert int(phase_n.get("insight_total_units") or 0) >= 6
    digest = _ROOT / "reports/logos_insight_synthesis_digest_v1_latest.md"
    assert digest.is_file()
    assert "Phase N" in digest.read_text(encoding="utf-8")
