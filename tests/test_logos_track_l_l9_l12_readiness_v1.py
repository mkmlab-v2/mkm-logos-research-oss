"""Track L L9–L12 public send readiness smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_logos_track_l_public_facing_readiness_v1() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_logos_track_l_public_facing_readiness_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "reports/logos_track_l_public_facing_readiness_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["ready_for_external_send"] is False
    assert doc["ready_for_internal_track_c_draft"] is True


def test_external_send_signoff_template_blocks_send() -> None:
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["schema"] == "logos_track_l_external_send_signoff_v1"
    assert doc["ready_for_external_send"] is False


def test_run_logos_track_l_l9_l12_readiness_v1_skip_l68() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_track_l_l9_l12_readiness_v1.py"),
            "--skip-l68",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_track_l_l9_l12_readiness_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["l9_l12_ok"] is True
    assert doc["ready_for_external_send"] is False


def test_record_commander_ack_keeps_external_send_false(tmp_path: Path) -> None:
    signoff = tmp_path / "signoff.json"
    signoff.write_text(
        json.dumps(
            {
                "schema": "logos_track_l_external_send_signoff_v1",
                "ready_for_external_send": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "ack.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/record_logos_track_l_commander_external_send_ack_v1.py"),
            "--signoff-json",
            str(signoff),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ready_for_external_send"] is False
