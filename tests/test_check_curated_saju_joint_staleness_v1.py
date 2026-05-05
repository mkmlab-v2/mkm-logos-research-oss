# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "check_curated_saju_joint_staleness_v1.py"


def test_stale_when_gap_exceeds_threshold(tmp_path: Path) -> None:
    curated = tmp_path / "in.jsonl"
    curated.write_text(
        json.dumps({"person_id": "x", "ingest_at_utc": "2026-01-01T00:00:00Z"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    bench = tmp_path / "bench.json"
    bench.write_text(
        json.dumps(
            {
                "generated_at_utc": "2025-01-01T00:00:00Z",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    p = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--curated-jsonl",
            str(curated),
            "--hit-rate-json",
            str(bench),
            "--threshold-hours",
            "24",
            "--out-json",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "STALE"


def test_ok_within_threshold(tmp_path: Path) -> None:
    t = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    curated = tmp_path / "in.jsonl"
    curated.write_text(json.dumps({"ingest_at_utc": t}, ensure_ascii=False) + "\n", encoding="utf-8")
    bench = tmp_path / "bench.json"
    bench.write_text(json.dumps({"generated_at_utc": t}, ensure_ascii=False) + "\n", encoding="utf-8")
    out = tmp_path / "out.json"
    p = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--curated-jsonl",
            str(curated),
            "--hit-rate-json",
            str(bench),
            "--threshold-hours",
            "8760",
            "--out-json",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "OK"
