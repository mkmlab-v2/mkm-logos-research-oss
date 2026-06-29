from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_phase_e_chain_exit0() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_b2b_phase_e_v1.py"),
            "--skip-evolution-loop",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    hub = (_ROOT / "reports/gwangmyeong_baekje_b2b_static_hub_draft_v1.md").read_text(encoding="utf-8")
    assert "logos_b2b_master_summary_v1" in hub
    assert "CLAIM-B2B-SCOPE" in hub

    ingest = json.loads(
        (_ROOT / "reports/logos_macula_themed_ingest_v1_latest.json").read_text(encoding="utf-8")
    )
    assert ingest.get("edges_built", 0) >= 50

    registry = json.loads(
        (
            _ROOT / "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert registry.get("schema") == "logos_reasoning_pattern_registry_v1"
    assert registry.get("content_domain_separation") is True


def test_apply_hub_requires_promoted_summary(tmp_path: Path) -> None:
    bad = tmp_path / "summary.json"
    bad.write_text(json.dumps({"promoted": False}), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/apply_logos_b2b_master_summary_to_hub_v1.py"),
            "--summary",
            str(bad),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cp.returncode != 0
