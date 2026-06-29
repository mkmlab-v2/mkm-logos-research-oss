"""Phase 11-O NL sandbox sync chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_logos_graphrag_phase11o_nl_sandbox_sync_chain_v1(tmp_path: Path) -> None:
    out = tmp_path / "phase11o_chain_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_graphrag_phase11o_nl_sandbox_sync_chain_v1.py"),
            "--skip-register",
            "--skip-push",
            "--skip-gate-spec",
            "--skip-evidence-pack",
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
    assert doc["schema"] == "logos_graphrag_phase11o_nl_sandbox_sync_chain_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["notebook_mcp_id"] == "14-universal-lexicon-dr"
    assert doc["pack_file_count"] == 7
