"""Tests for scripts/ingest_notebooklm_metabolism_jsonl.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ingest_notebooklm_metabolism_jsonl.py"
FIXTURE = ROOT / "docs" / "final" / "artifacts" / "fixtures" / "log_metabolism_smoke_v1.jsonl"


def _run_ingest(raw: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    inp = tmp_path / "raw.txt"
    out = tmp_path / "out.jsonl"
    inp.write_text(raw, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--in", str(inp), "--out", str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_plain_jsonl_roundtrip(tmp_path: Path) -> None:
    body = FIXTURE.read_text(encoding="utf-8")
    cp = _run_ingest(body, tmp_path)
    assert cp.returncode == 0, cp.stderr
    out = (tmp_path / "out.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(out) == 3
    for line in out:
        o = json.loads(line)
        assert set(["window_start_utc", "egress_pressure", "throttle_events"]).issubset(o.keys())


def test_markdown_fences_stripped(tmp_path: Path) -> None:
    body = "```json\n" + FIXTURE.read_text(encoding="utf-8").strip() + "\n```\n"
    cp = _run_ingest(body, tmp_path)
    assert cp.returncode == 0, cp.stderr
    lines = (tmp_path / "out.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_json_array_whole_file(tmp_path: Path) -> None:
    rows = [json.loads(x) for x in FIXTURE.read_text(encoding="utf-8").strip().splitlines()]
    body = json.dumps(rows, indent=2)
    cp = _run_ingest(body, tmp_path)
    assert cp.returncode == 0, cp.stderr
    lines = (tmp_path / "out.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_nlm_json_wrapper_value_content(tmp_path: Path) -> None:
    inner = FIXTURE.read_text(encoding="utf-8").strip()
    wrapped = json.dumps({"value": {"content": inner, "title": "x"}}, ensure_ascii=False)
    cp = _run_ingest(wrapped, tmp_path)
    assert cp.returncode == 0, cp.stderr
    lines = (tmp_path / "out.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_dry_run_ok(tmp_path: Path) -> None:
    inp = tmp_path / "raw.txt"
    inp.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--in",
            str(inp),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout.strip())
    assert doc.get("dry_run_ok") is True
    assert doc.get("valid_rows") == 3


def test_missing_key_fails_no_output(tmp_path: Path) -> None:
    bad = '{"window_start_utc":"2026-01-01T00:00:00Z","egress_pressure":1}\n'
    cp = _run_ingest(bad, tmp_path)
    assert cp.returncode == 1
    out = tmp_path / "out.jsonl"
    assert not out.is_file()
