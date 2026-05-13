"""convert_myeongri_golden_to_sft_instruction_jsonl_v1: one-row round-trip smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CONVERTER = _REPO / "scripts" / "convert_myeongri_golden_to_sft_instruction_jsonl_v1.py"
_FIXTURE = _REPO / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"


def test_converter_emits_instruction_output(tmp_path: Path) -> None:
    out = tmp_path / "sft.jsonl"
    r = subprocess.run(
        [
            sys.executable,
            str(_CONVERTER),
            "--input-jsonl",
            str(_FIXTURE),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1
    row = json.loads(lines[0])
    assert "instruction" in row and "output" in row
    assert "saju_global_birth_result" in row["output"] or "full_saju" in row["output"]
