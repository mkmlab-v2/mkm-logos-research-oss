from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_themed_graphrag_seed_audit_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/audit_logos_themed_graphrag_seed_retrieval_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (_ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("schema") == "logos_themed_graphrag_seed_retrieval_v1"
    assert len(doc.get("themes") or []) == 2
    assert "seed_hits_organic" in (doc.get("summary") or {})


def test_phase_g_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_phase_g_v1.py"),
            "--skip-phase-f",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    digest = (_ROOT / "reports/logos_track_b_commander_dual_theme_digest_latest.md").read_text(encoding="utf-8")
    assert "GraphRAG 시드 회수" in digest
    assert "retrieval recall@5" in digest
    assert "B2B 논리 이식" in digest

    phase_g = json.loads((_ROOT / "reports/logos_track_b_phase_g_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_g.get("ok") is True
