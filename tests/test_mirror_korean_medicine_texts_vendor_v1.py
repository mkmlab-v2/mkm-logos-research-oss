"""KM classics vendor mirror v1 [HYPO]."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mirror_korean_medicine_texts_vendor_v1 import build_mirror_report  # noqa: E402

STUB = ROOT / "tests/fixtures/km_classics_vendor_stub_hypo_v1"


def test_mirror_report_stub_fixture(tmp_path: Path) -> None:
    doc = build_mirror_report(STUB, clone_action="stub_fixture")
    assert doc["schema"] == "km_classics_vendor_mirror_v1"
    assert doc["personadiary_join"] is False
    assert doc["clinician_lane_only"] is True


def test_cli_skip_clone_writes_report(tmp_path: Path) -> None:
    out = tmp_path / "mirror.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/mirror_korean_medicine_texts_vendor_v1.py"),
            "--skip-clone",
            "--vendor-root",
            str(STUB),
            "--out-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["clone_action"] == "stub_fixture"
    assert doc["commit_sha"] == "stub-no-git"
