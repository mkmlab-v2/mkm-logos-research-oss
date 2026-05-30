"""Smoke: offline_4d strict commander review pack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_logos_offline_4d_strict_review_pack_v1.py"
OUT_JSON = ROOT / "reports" / "logos_offline_4d_strict_review_pack_v1_latest.json"


def test_offline_4d_strict_review_pack_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert OUT_JSON.is_file()
    doc = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_offline_4d_strict_review_pack_v1"
    assert doc["bulk_merge_blocked"] is True
    assert len(doc["items"]) == 5
    ranks = {i["queue_rank"] for i in doc["items"]}
    assert ranks == {46, 47, 48, 49, 50}
