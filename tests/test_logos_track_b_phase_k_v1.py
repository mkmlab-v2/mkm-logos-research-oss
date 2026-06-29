from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_router_graph_paths_sync() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/sync_logos_themed_router_graph_paths_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (_ROOT / "reports/logos_themed_router_graph_paths_sync_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("ok") is True
    locked = json.loads(
        (
            _ROOT / "docs/final/artifacts/logos_deep_research_distill_john_1_logos_citation_lock_latest.json"
        ).read_text(encoding="utf-8")
    )
    paths = locked.get("graph_paths") or []
    assert any(p.get("edge_type") == "graphrag_router_path" for p in paths if isinstance(p, dict))


def test_phase_k_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_track_b_phase_k_v1.py"),
            "--skip-phase-j",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    phase_k = json.loads((_ROOT / "reports/logos_track_b_phase_k_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_k.get("ok") is True
    assert phase_k.get("graph_paths_router_sync", {}).get("ok") is True
