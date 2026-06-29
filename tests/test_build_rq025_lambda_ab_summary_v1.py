from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_rq025_lambda_ab_summary_v1.py"
THREE = ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json"


def test_build_rq025_ab_summary(tmp_path: Path) -> None:
    if not THREE.is_file():
        import pytest

        pytest.skip("three-arm report missing")
    out_json = tmp_path / "ab.json"
    out_md = tmp_path / "ab.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "rq025_lambda_ab_summary_v1"
    assert len(doc.get("arms") or []) >= 2
    assert "proxy" in out_md.read_text(encoding="utf-8")
