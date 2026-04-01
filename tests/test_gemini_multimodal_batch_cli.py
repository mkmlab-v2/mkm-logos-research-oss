# -*- coding: utf-8 -*-
"""scripts/gemini_multimodal_batch.py — 네트워크·API 키 없이 CLI 구조만 검증."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gemini_multimodal_batch.py"


def _run(*args: str, timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def test_script_exists():
    assert SCRIPT.is_file(), SCRIPT


def test_check_subcommand_ok():
    r = _run("check")
    assert r.returncode == 0, r.stderr
    assert "google.genai" in r.stdout
    assert "GEMINI_API_KEY" in r.stdout or "GOOGLE_API_KEY" in r.stdout


def test_research_help_includes_timeout():
    r = _run("research", "--help")
    assert r.returncode == 0, r.stderr
    assert "--timeout" in r.stdout


def test_image_help_includes_timeout():
    r = _run("image", "--help")
    assert r.returncode == 0, r.stderr
    assert "--timeout" in r.stdout


def test_crosscheck_help_includes_timeout():
    r = _run("crosscheck", "--help")
    assert r.returncode == 0, r.stderr
    assert "--timeout" in r.stdout


def test_main_missing_key_returns_2_for_research(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    r = _run("research", "-f", str(ROOT / "pytest.ini"), "-p", "x")
    assert r.returncode == 2
    combined = (r.stderr or "") + (r.stdout or "")
    assert "필요" in combined or "required" in combined.lower() or "GEMINI" in combined
