"""bench_l1_api_load.py dry-run schema (no live stub required)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bench_l1_api_load.py"


def test_bench_l1_api_load_dry_run_schema() -> None:
    with tempfile.TemporaryDirectory() as td:
        outp = Path(td) / "bench_out.json"
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--dry-run",
                "--out",
                str(outp),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr
        assert outp.is_file()
        data = json.loads(outp.read_text(encoding="utf-8"))
    assert data.get("schema") == "bench_l1_api_load_v1"
    assert data.get("dry_run") is True


def test_bench_l1_api_load_bench_environment_in_dry_run() -> None:
    with tempfile.TemporaryDirectory() as td:
        outp = Path(td) / "bench_out_env.json"
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--dry-run",
                "--bench-environment",
                "vps_same_host",
                "--out",
                str(outp),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(outp.read_text(encoding="utf-8"))
    assert data.get("bench_environment") == "vps_same_host"
