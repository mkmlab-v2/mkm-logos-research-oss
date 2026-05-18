from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.myeongri_deterministic_lora_golden_views_v1 import (
    compact_expected_result,
    instruction_from_golden_row,
    pillars_view,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"


def test_compact_strips_daewoon() -> None:
    row = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    exp = row["expected_result"]
    assert "daewoon" in exp.get("full_saju", {})
    compact = compact_expected_result(exp)
    assert "daewoon" not in compact.get("full_saju", {})


def test_pillars_view_stable_keys() -> None:
    row = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    pv = pillars_view(row["expected_result"])
    assert pv["full_saju"]["saju"]
    assert "daewoon" not in pv.get("full_saju", {})


def test_compact_convert_smoke(tmp_path: Path) -> None:
    out = tmp_path / "sft.jsonl"
    script = ROOT / "scripts" / "convert_myeongri_golden_to_sft_instruction_jsonl_v1.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-jsonl",
            str(FIXTURE),
            "--output-jsonl",
            str(out),
            "--compact-output",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    line = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert "daewoon" not in line["output"]
    assert "omit daewoon" in line["instruction"]


def test_oracle_pillars_tier_on_fixture(tmp_path: Path) -> None:
    report = tmp_path / "eval.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_myeongri_deterministic_lora_inference_eval_v1.py"),
            "--golden-jsonl",
            str(FIXTURE),
            "--oracle-golden",
            "--alignment-tier",
            "pillars",
            "--report-json",
            str(report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["alignment_pass_rate"] == 1.0
    assert doc["alignment_tier"] == "pillars"


def test_instruction_compact_flag() -> None:
    row = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    full = instruction_from_golden_row(row, compact_output=False)
    compact = instruction_from_golden_row(row, compact_output=True)
    assert "omit daewoon" in compact
    assert "omit daewoon" not in full
    assert "do not invent" in compact.lower()
    assert row["birth_instant_utc"] in compact
