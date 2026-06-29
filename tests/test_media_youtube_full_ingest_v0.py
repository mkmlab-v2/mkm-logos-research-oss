"""Full YouTube transcript ingest + diff report smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "tests/fixtures/youtube_transcript_polluted_full_v0.txt"
DIFF = ROOT / "scripts/build_media_youtube_ingest_diff_report_v0.py"
REPORT = ROOT / "reports/media_youtube_ingest_diff_v0_latest.json"


def test_full_transcript_file_exists_and_substantial() -> None:
    text = FULL.read_text(encoding="utf-8")
    assert len(text) >= 5000
    assert "0:00" in text
    assert "시친" in text
    assert "엘로힘" in text


def test_full_ingest_diff_report_cli(tmp_path: Path) -> None:
    out = tmp_path / "diff.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(DIFF),
            "--input",
            str(FULL),
            "--out",
            str(out),
            "--merge-min-chars",
            "650",
            "--merge-max-chars",
            "1300",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "media_youtube_ingest_diff_v0"
    assert doc["parsed_block_count"] >= 50
    assert 12 <= doc["ingest"]["segment_count"] <= 40
    assert doc["ingest"]["debunked_in_scholarly_lane"] == 0
    assert len(doc["ingest"]["scholarly_top3"]) == 3
    assert doc["ingest"]["provenance_counts"].get("debunked_fake", 0) >= 3
    prox = doc.get("diff", {}).get("scholarly_top3_proximity") or {}
    assert prox.get("overlap_count", 0) >= 1
    mdl = doc.get("layer_c_mdl_poc") or {}
    scholarly_mdl = mdl.get("scholarly_top1") or {}
    assert scholarly_mdl.get("char_saving_rate", 0) >= 0.0
    assert len(mdl.get("multilens_top3") or []) == 3
    for row in mdl.get("multilens_top3") or []:
        assert row.get("char_saving_rate", 0) >= 0.0
        assert row.get("segment_id")


def test_full_ingest_handoff_has_layer_c_section() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_media_youtube_full_ingest_chain_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    handoff = ROOT / "reports/handoff_workers/HW-20260621-YT-FULL-LOGOS_CLIP.md"
    text = handoff.read_text(encoding="utf-8")
    assert "2c. Layer C MDL" in text
    assert "Scholarly Top-1" in text
    assert "Multilens Top clips" in text
