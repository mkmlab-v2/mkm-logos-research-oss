# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "final" / "artifacts" / "fixtures" / "log_metabolism_smoke_v1.jsonl"


def test_convert_script_smoke(tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    import subprocess
    import sys

    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "convert_log_metabolism_to_myeongri_correlation_input_v1.py"),
            "--in",
            str(FIXTURE),
            "--out",
            str(out),
            "--run-id",
            "pytest_convert_v1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0, r.stderr
    lines = [x for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 3
    row = json.loads(lines[0])
    assert row["schema"] == "log_myeongri_correlation_input_row_v1"
    assert row["run_metadata"]["run_id"] == "pytest_convert_v1"
    assert "total_requests" in row["metrics"]
