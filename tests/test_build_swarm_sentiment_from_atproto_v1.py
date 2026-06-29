"""Smoke: ATProto raw → tier_a Swarm JSONL ingest."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATPROTO_DIR = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "atproto"
)


def test_build_swarm_sentiment_from_atproto_v1_smoke(tmp_path: Path) -> None:
    if not ATPROTO_DIR.is_dir():
        return
    raw_files = list(ATPROTO_DIR.glob("*_atproto_sentiment_raw.jsonl"))
    if not raw_files:
        return

    out = tmp_path / "real_pit.jsonl"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_swarm_sentiment_from_atproto_v1.py"),
        "--atproto-dir",
        str(ATPROTO_DIR),
        "--out-jsonl",
        str(out),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr or r.stdout

    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1
    row = json.loads(lines[0])
    assert row.get("seed_cutoff_time")
    meta = row.get("simulation_meta") or {}
    assert meta.get("engine_name") == "atproto_operational_heuristic_v1"
    assert "T09:00:00Z" in str(row.get("seed_cutoff_time"))
