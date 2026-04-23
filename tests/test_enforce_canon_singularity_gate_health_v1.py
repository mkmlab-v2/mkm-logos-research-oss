from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_enforce_canon_singularity_gate_health_v1_pass(tmp_path: Path):
    src = tmp_path / "health.json"
    out = tmp_path / "eval.json"
    src.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_quality_gate_health_summary_v1",
                "health_level": "green",
                "counts": {"fail_count": 0, "pass_rate": 1.0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/enforce_canon_singularity_gate_health_v1.py",
        "--health-summary-json",
        str(src),
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "pass"


def test_enforce_canon_singularity_gate_health_v1_fail(tmp_path: Path):
    src = tmp_path / "health.json"
    out = tmp_path / "eval.json"
    src.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_quality_gate_health_summary_v1",
                "health_level": "yellow",
                "counts": {"fail_count": 1, "pass_rate": 0.5},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/enforce_canon_singularity_gate_health_v1.py",
        "--health-summary-json",
        str(src),
        "--max-fail-count",
        "0",
        "--min-pass-rate",
        "0.9",
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "fail"
    assert len(data["reasons"]) >= 1

