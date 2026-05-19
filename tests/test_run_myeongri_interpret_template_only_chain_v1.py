"""Template-only interpret chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl"


def test_template_only_chain_on_fixture(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_myeongri_interpret_template_only_chain_v1.py"),
            "--golden-jsonl",
            str(FIXTURE),
            "--out-json",
            str(out),
            "--limit",
            "2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["engine_pillars_pass_rate"] == 1.0
    assert doc["envelope_schema_valid_rate"] == 1.0
