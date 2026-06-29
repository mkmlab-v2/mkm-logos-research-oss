"""Smoke: extract input merge + dogfood session + extract gate n7."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_extract_input_merged() -> None:
    out = ROOT / "data/btrack/cursor_coding_agent_extract_input_test.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/build_cursor_coding_agent_extract_input_v1.py"),
            "--out-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 7


def test_dogfood_session_strict() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/run_prism_meta_channel_dogfood_session_v1.py"),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(
        (ROOT / "reports/dogfood_meta_channel_session_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("session_pass") is True


def test_extract_gate_all_seven_pass() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/sandbox/build_cursor_coding_agent_extract_input_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_cursor_coding_agent_extract_gate_v1.py"),
            "--out-json",
            str(ROOT / "reports/cursor_coding_agent_extract_gate_v1_test.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(
        (ROOT / "reports/cursor_coding_agent_extract_gate_v1_test.json").read_text(encoding="utf-8")
    )
    assert doc.get("gate", {}).get("pass") is True
    assert len(doc.get("cases") or []) == 7
