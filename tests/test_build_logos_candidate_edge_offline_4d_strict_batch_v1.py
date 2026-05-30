"""Smoke: offline_4d strict LoRA micro-batch builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_logos_candidate_edge_offline_4d_strict_batch_v1.py"
OUT_BATCH = ROOT / "reports/logos_candidate_edge_offline_4d_lora_strict_batch_v1_latest.json"
OUT_FILTERED = ROOT / "docs/final/artifacts/logos_review_queue_offline_4d_strict_v1_latest.json"


def test_offline_4d_strict_batch_builder_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert OUT_BATCH.is_file()
    assert OUT_FILTERED.is_file()
    batch = json.loads(OUT_BATCH.read_text(encoding="utf-8"))
    filtered = json.loads(OUT_FILTERED.read_text(encoding="utf-8"))
    assert batch["schema"] == "logos_candidate_edge_offline_4d_lora_strict_batch_v1"
    assert batch["bulk_merge_blocked"] is True
    assert batch["lora_strict_only"] is True
    assert batch["pending_only"] is True
    n = len(batch["items"])
    assert 0 <= n <= 5
    assert filtered["stats"]["selected_count"] == n
    if n == 0:
        # Queue satiation: all offline_4d rows decided — builder still exits 0.
        return
    assert n == 5
    assert all(i.get("lane_id") == "offline_4d_knn" for i in filtered["items"])
    assert all(not i.get("review_decision") for i in filtered["items"])
