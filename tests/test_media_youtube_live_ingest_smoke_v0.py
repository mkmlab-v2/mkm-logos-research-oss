"""Live YouTube ingest smoke + handoff closure Layer C checks."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIVE_SMOKE = ROOT / "scripts/run_media_youtube_live_ingest_smoke_v0.py"
CLOSURE = ROOT / "scripts/verify_handoff_closure_v1.py"


def test_live_youtube_fetch_and_parse_smoke() -> None:
    pytest.importorskip("youtube_transcript_api")
    proc = subprocess.run(
        [sys.executable, str(LIVE_SMOKE), "--youtube-url", "https://youtu.be/jNQXAC9IVRw"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = json.loads((ROOT / "reports/media_youtube_live_ingest_smoke_v0_latest.json").read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["parse"]["block_count"] >= 1
    assert report["parse"]["segment_count"] >= 1


def test_fetch_api_normalizes_fetched_transcript_snippets() -> None:
    pytest.importorskip("youtube_transcript_api")
    from scripts.fetch_youtube_transcript_v0 import fetch_youtube_transcript_v0

    out = fetch_youtube_transcript_v0("jNQXAC9IVRw", languages=("en",), dry_run=False)
    assert out.get("ok") is True
    assert out.get("snippet_count", 0) >= 1
    assert re.match(r"0:\d{2}", str(out.get("text") or ""))


def test_closure_auto_checks_layer_c_for_yt_full_handoff() -> None:
    handoff = ROOT / "reports/handoff_workers/HW-20260621-YT-FULL-LOGOS_CLIP.md"
    if not handoff.is_file():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_media_youtube_full_ingest_chain_v1.py")],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    proc = subprocess.run(
        [
            sys.executable,
            str(CLOSURE),
            "--task-id",
            "20260621-YT-FULL",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    closure = json.loads(
        (ROOT / "reports/handoff_workers/HW-20260621-YT-FULL-closure.json").read_text(encoding="utf-8")
    )
    checks = closure.get("layer_c_mdl_checks") or {}
    assert checks.get("present") is True
    assert checks.get("ok") is True
