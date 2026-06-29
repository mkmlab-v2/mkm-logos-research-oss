"""Polluted bench SSOT + live/fixture ingest orchestrator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "scripts/run_media_polluted_bench_live_ingest_v0.py"
SSOT = ROOT / "tests/fixtures/media_polluted_bench_youtube_ssot_v1.json"


def test_ssot_fixture_fingerprint_passes() -> None:
    from scripts.load_media_polluted_bench_ssot_v0 import (
        load_media_polluted_bench_ssot_v0,
        read_fixture_transcript,
        transcript_fingerprint_v0,
    )

    ssot = load_media_polluted_bench_ssot_v0(SSOT)
    text = read_fixture_transcript(ssot)
    fp = transcript_fingerprint_v0(
        text,
        list(ssot["fingerprint_keywords"]),
        min_hits=int(ssot["fingerprint_min_hits"]),
    )
    assert fp["pass"] is True
    assert fp["hit_count"] >= 4


def test_fixture_replay_orchestrator_exit_0() -> None:
    proc = subprocess.run(
        [sys.executable, str(ORCH), "--fixture"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = json.loads((ROOT / "reports/media_polluted_bench_live_ingest_v0_latest.json").read_text(encoding="utf-8"))
    assert report["mode"] == "fixture_replay"
    assert report["ok"] is True
    assert report["closure"]["exit_code"] == 0


def test_live_mode_requires_url_env() -> None:
    env = os.environ.copy()
    env.pop("MKM_POLLUTED_BENCH_YOUTUBE_URL", None)
    proc = subprocess.run(
        [sys.executable, str(ORCH), "--live"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
