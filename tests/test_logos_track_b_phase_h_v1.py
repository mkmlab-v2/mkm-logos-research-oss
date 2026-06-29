from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_themed_anchor_bridge_builds() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/build_logos_themed_anchor_concept_bridge_v1.py"),
            "--theme",
            "john_1_logos",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    bridge = json.loads(
        (
            _ROOT / "docs/final/artifacts/logos_concept_bridge_themed_john_1_logos_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert len(bridge.get("paths") or []) >= 10
    hooks = bridge.get("graph_rag_hooks") or {}
    assert len(hooks.get("seed_verse_ids") or []) >= 10


def test_phase_h_chain_exit0() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_logos_track_b_phase_h_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    audit = json.loads(
        (_ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json").read_text(encoding="utf-8")
    )
    sm = audit.get("summary") or {}
    organic = sm.get("seed_hits_organic", "0/0")
    num = int(organic.split("/")[0])
    assert num >= 10, f"expected organic seed hits >=10, got {organic}"

    john = next(t for t in audit.get("themes") or [] if t["theme_id"] == "john_1_logos")
    assert john.get("seed_hit_organic", "0/0").startswith(("6/", "7/", "8/", "9/", "1"))

    phase_h = json.loads((_ROOT / "reports/logos_track_b_phase_h_v1_latest.json").read_text(encoding="utf-8"))
    assert phase_h.get("ok") is True
    assert phase_h.get("wiring_ok") is True
