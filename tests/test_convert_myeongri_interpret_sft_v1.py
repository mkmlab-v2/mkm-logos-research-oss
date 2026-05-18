"""Interpret SFT convert: envelope schema + instruction wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "myeongri_deterministic_lora_golden_sample_v1.jsonl"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "myeongri_ai_interpretation_envelope_v1.schema.json"


def test_strip_chat_leakage() -> None:
    from scripts.myeongri_interpret_envelope_views_v1 import strip_chat_leakage

    raw = '{"schema":"myeongri_ai_interpretation_envelope_v1"}Human: follow up'
    assert "Human:" not in strip_chat_leakage(raw)


def test_convert_interpret_sft_smoke(tmp_path: Path) -> None:
    out = tmp_path / "interpret_sft.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "convert_myeongri_golden_to_interpret_sft_jsonl_v1.py"),
            "--input-jsonl",
            str(FIXTURE),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    line = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert "myeongri_ai_interpretation_envelope_v1" in line["instruction"]
    out_obj = json.loads(line["output"])
    assert out_obj["schema"] == "myeongri_ai_interpretation_envelope_v1"
    assert out_obj["hypothesis_tier"] == "B"
    assert "[HYPO]" in out_obj["mkm_advanced_insight"]


def test_interpret_sft_output_validates_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "interpret_sft.jsonl"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "convert_myeongri_golden_to_interpret_sft_jsonl_v1.py"),
            "--input-jsonl",
            str(FIXTURE),
            "--output-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )
    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    obj = json.loads(row["output"])
    jsonschema.Draft7Validator(schema).validate(obj)
