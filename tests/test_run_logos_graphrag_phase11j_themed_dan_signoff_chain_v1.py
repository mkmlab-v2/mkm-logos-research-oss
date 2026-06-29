"""Phase 11-J themed_dan signoff chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_logos_graphrag_phase11j_themed_dan_signoff_chain_v1(tmp_path: Path) -> None:
    out = tmp_path / "phase11j_chain_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_graphrag_phase11j_themed_dan_signoff_chain_v1.py"),
            "--skip-signoff",
            "--skip-gold-eval",
            "--skip-evidence-pack",
            "--skip-sweep-refresh",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_graphrag_phase11j_themed_dan_signoff_chain_v1"
    assert doc["concept_id"] == "concept:themed_dan_aramaic"
    assert doc["human_signoff_completed"] is True
