"""smoke_docling_btrack_v1 contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/btrack_fixtures/docling_smoke_v1.md"
SCRIPT = ROOT / "scripts/smoke_docling_btrack_v1.py"


def test_fixture_present() -> None:
    assert FIXTURE.is_file()


def test_smoke_fixture_only_writes_ok() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--fixture-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["status"] == "ok_fixture_only"


def test_smoke_cli_writes_json(tmp_path: Path) -> None:
    out_json = tmp_path / "smoke.json"
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(FIXTURE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode in (0, 1), proc.stderr
    data = json.loads(proc.stdout or proc.stderr)
    assert data["schema"] == "docling_btrack_smoke_v1"
    assert data["status"] in {"ok", "skip", "fail"}
