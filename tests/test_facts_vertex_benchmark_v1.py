"""run_facts_vertex_benchmark_v1: JSON parse + dry-run pipeline (no Vertex network)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_facts_vertex_benchmark_v1.py"
FIXTURE_AK = ROOT / "tests/fixtures/facts_minimal_answer_key.sample.jsonl"


def test_script_exists() -> None:
    assert SCRIPT.is_file()


def test_extract_json_fenced_markdown() -> None:
    from scripts.run_facts_vertex_benchmark_v1 import _extract_json_object

    text = """Here:\n```json\n{\n  \"decision\": \"ANSWER\",\n  \"prediction\": \"Paris\"\n}\n```"""
    obj = _extract_json_object(text)
    assert obj["decision"] == "ANSWER"
    assert obj["prediction"] == "Paris"


def test_extract_json_plain() -> None:
    from scripts.run_facts_vertex_benchmark_v1 import _extract_json_object

    obj = _extract_json_object('{"decision":"HOLD","prediction":""}')
    assert obj["decision"] == "HOLD"


def test_dry_run_end_to_end(tmp_path: Path) -> None:
    pred = tmp_path / "pred.jsonl"
    ev = tmp_path / "eval.json"
    rep = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--answer-key-jsonl",
            str(FIXTURE_AK),
            "--out-predictions-jsonl",
            str(pred),
            "--out-eval-json",
            str(ev),
            "--out-report-json",
            str(rep),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    body = json.loads(rep.read_text(encoding="utf-8"))
    assert body["schema"] == "facts_vertex_benchmark_v1"
    assert body["dry_run"] is True
    assert body["eval"]["metrics"]["coverage"] == 1.0


def test_limit_slices_answer_key(tmp_path: Path) -> None:
    pred = tmp_path / "pred.jsonl"
    ev = tmp_path / "eval.json"
    rep = tmp_path / "report.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--answer-key-jsonl",
            str(FIXTURE_AK),
            "--limit",
            "2",
            "--out-predictions-jsonl",
            str(pred),
            "--out-eval-json",
            str(ev),
            "--out-report-json",
            str(rep),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    report = json.loads(rep.read_text(encoding="utf-8"))
    assert report["eval"]["metrics"]["total_answer_key"] == 2
