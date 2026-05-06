"""LLM-style fenced / noisy text → JSON extract for logos_response_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "logos_response_v1_llm_fenced_sample.txt"
SCRIPT = ROOT / "scripts" / "logos_response_validator_v1.py"


def test_parse_llm_payload_import() -> None:
    from scripts.logos_response_validator_v1 import parse_llm_payload

    raw = FIXTURE.read_text(encoding="utf-8")
    doc = parse_llm_payload(raw, strict=False)
    assert doc.get("schema") == "logos_response_v1"
    assert doc.get("corpus_profile_id") == "canon_only_v1"


def test_pipeline_on_fenced_file_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "pipeline", "-i", str(FIXTURE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "성경 고도화 해석 브리핑" in r.stdout


def test_extract_writes_normalized_json(tmp_path) -> None:
    out = tmp_path / "out.json"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "extract", "-i", str(FIXTURE), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_response_v1"
