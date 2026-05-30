"""Smoke: offline_4d strict commander review pack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_logos_offline_4d_strict_review_pack_v1.py"
# Frozen wave artifact (stable when live queue has no pending offline_4d).
SUBSET = ROOT / "docs/final/artifacts/logos_review_queue_offline_4d_strict_wave12_v1_latest.json"
BATCH = ROOT / "reports/logos_candidate_edge_offline_4d_lora_strict_batch_wave12_v1_latest.json"
OUT_JSON = ROOT / "reports/logos_offline_4d_strict_review_pack_v1_latest.json"


def test_offline_4d_strict_review_pack_smoke() -> None:
    assert SUBSET.is_file(), f"missing fixture subset: {SUBSET}"
    assert BATCH.is_file(), f"missing fixture batch: {BATCH}"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--wave",
            "12",
            "--subset-json",
            str(SUBSET),
            "--batch-json",
            str(BATCH),
            "--output-json",
            str(OUT_JSON),
            "--output-md",
            str(OUT_JSON.with_suffix(".md")),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT_JSON.is_file()
    doc = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_offline_4d_strict_review_pack_v1"
    assert doc["bulk_merge_blocked"] is True
    assert len(doc["items"]) == 5
    ranks = {i["queue_rank"] for i in doc["items"]}
    assert ranks == {96, 97, 98, 99, 100}
