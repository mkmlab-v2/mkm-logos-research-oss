"""L4 commander scope sign-off."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_record_l4_rejects_without_l3(tmp_path: Path):
    bad_l3 = tmp_path / "l3.json"
    bad_l3.write_text(json.dumps({"acknowledged": False}), encoding="utf-8")
    prep = tmp_path / "prep.json"
    prep.write_text(
        json.dumps({"summary_metrics": {"nested_revalidation_pass": True}}),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            PY,
            "scripts/record_kospi_field_band_commander_l4_sign_v1.py",
            "--sign-reference",
            "TEST-L4",
            "--l3-ack-json",
            str(bad_l3),
            "--prep-json",
            str(prep),
            "--out-json",
            str(tmp_path / "out.json"),
            "--log-jsonl",
            str(tmp_path / "log.jsonl"),
            "--skip-local",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cp.returncode != 0


@pytest.mark.skipif(
    not (ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_v1_latest.json").is_file(),
    reason="L3 ack missing",
)
def test_record_l4_sign_exit_zero():
    cp = subprocess.run(
        [
            PY,
            "scripts/record_kospi_field_band_commander_l4_sign_v1.py",
            "--sign-reference",
            "COMMANDER-KOSPI-BAND-L4-SIGN-2026-06-23",
            "--skip-local",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/kospi_field_band_commander_l4_sign_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert doc["signed"] is True
    assert doc["track_a_go"] is False
    assert doc["send_gate"] == "HOLD"
