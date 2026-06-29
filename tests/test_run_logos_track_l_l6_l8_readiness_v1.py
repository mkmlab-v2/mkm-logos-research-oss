"""Track L L6–L8 S1 shadow advisory readiness smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_logos_track_l_l6_l8_readiness_v1_skip_l45() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_track_l_l6_l8_readiness_v1.py"),
            "--skip-l45",
            "--rebuild-packet",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_track_l_l6_l8_readiness_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "logos_track_l_l6_l8_readiness_v1"
    assert doc["l6_l8_ok"] is True
    assert doc["checks"]["review_packet"]["track_l_label"] == "Track L"


def test_human_approval_includes_track_l_advisory(tmp_path: Path) -> None:
    kpi = tmp_path / "kpi.json"
    out = tmp_path / "approval.json"
    kpi.write_text(
        json.dumps(
            {"status": "READY_FOR_REVIEW", "passed": True, "checks": {}},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/record_logos_s1_shadow_promotion_human_approval_v1.py"),
            "--kpi-progress-json",
            str(kpi),
            "--output-json",
            str(out),
            "--skip-agent-decision-log",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    track_l = doc.get("track_l_advisory") or {}
    assert track_l.get("label") == "Track L"
    assert track_l.get("non_gating") is True
