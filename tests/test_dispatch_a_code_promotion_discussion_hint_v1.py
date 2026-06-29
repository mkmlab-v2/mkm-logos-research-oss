"""A-code promotion discussion hint dispatch tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/dispatch_a_code_promotion_discussion_hint_v1.py"
READINESS = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"


def test_dispatch_skips_when_not_eligible(tmp_path: Path) -> None:
    readiness = {
        "schema": "a_code_promotion_checklist_readiness_v1",
        "summary": {"promotion_discussion_eligible": False},
    }
    readiness_path = tmp_path / "ready.json"
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
    out = tmp_path / "dispatch.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--readiness", str(readiness_path), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["dispatch_status"] == "skipped_not_eligible"


@pytest.mark.skipif(not READINESS.is_file(), reason="readiness artifact missing")
def test_dispatch_dry_run_when_eligible(tmp_path: Path) -> None:
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    if readiness.get("summary", {}).get("promotion_discussion_eligible") is not True:
        pytest.skip("promotion_discussion_eligible not true in latest artifact")
    out = tmp_path / "dispatch.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness",
            str(READINESS),
            "--out",
            str(out),
            "--dry-run",
            "--webhook-url",
            "https://example.invalid/hook",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["promotion_discussion_eligible"] is True
    assert doc["dispatch_status"] == "dry_run"


def test_promotion_discussion_append_line_import() -> None:
    import importlib.util

    path = ROOT / "scripts/a_code_evening_briefing_append_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_evening_append", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    line = mod.promotion_discussion_append_line(ROOT / "reports/nonexistent.json")
    assert line is None
