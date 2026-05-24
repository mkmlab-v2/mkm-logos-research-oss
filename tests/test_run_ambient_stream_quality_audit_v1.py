"""Zone A quality audit — structure and missing-file hold."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_ambient_stream_quality_audit_v1 import build_audit


def test_audit_holds_when_video_missing(tmp_path: Path) -> None:
    manifest = tmp_path / "reports/ambient_stream_manifest_latest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "caption_config": {"disclaimer_text_ko": "면책"},
                "brand_overlay": {"title_ko": "T", "subtitle_ko": "S"},
            }
        ),
        encoding="utf-8",
    )
    bed = tmp_path / "reports/audio/mkm_ambient_bed_loop_latest.wav"
    bed.parent.mkdir(parents=True)
    bed.write_bytes(b"RIFF" + b"\0" * 100)

    doc = build_audit(tmp_path, preview_seconds=5.0, write_preview=False)
    assert doc["broadcast_ready"] is False
    assert "missing_oracle_sphere_mp4" in doc["issues"]
