"""Tests for lens media (audio+video) observability builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lens_media_observability_smoke(tmp_path: Path) -> None:
    video_lut = tmp_path / "video_lut.json"
    video_lut.write_text(
        json.dumps(
            {
                "schema": "jemaai_lens_video_playback_lut_v1",
                "version": "2026-06-07",
                "hypothesis_class": "HYPO",
                "assets_base_url": "https://jemaai.cloud/video/lens_btrack/v1/",
                "entries": {
                    "LV_HP050_SOYANG_IDLE_V1": {
                        "file": "lv_hp050_soyang_idle_v1.webm",
                        "sasang_primary": "soyang",
                        "showroom_display_mode": "idle",
                        "gate_decision": "WATCH",
                        "duration_sec": 12,
                        "audio_playback_id_mirror": "LM_HP050_SOYANG_IDLE_V1",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    audio_out = tmp_path / "audio.json"
    video_out = tmp_path / "video.json"
    slice_out = tmp_path / "slice.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_showroom_lens_media_observability_v1.py"),
            "--showroom-display-mode",
            "idle",
            "--audio-out-json",
            str(audio_out),
            "--video-out-json",
            str(video_out),
            "--media-slice-out",
            str(slice_out),
            "--video-lut",
            str(video_lut),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    audio = json.loads(audio_out.read_text(encoding="utf-8"))
    video = json.loads(video_out.read_text(encoding="utf-8"))
    slice_doc = json.loads(slice_out.read_text(encoding="utf-8"))

    assert audio["schema"] == "public_event_lens_audio_thin_slice_v1"
    assert video["schema"] == "public_event_lens_video_thin_slice_v1"
    assert video["video_playback_id"] == "LV_HP050_SOYANG_IDLE_V1"
    assert video["audio_playback_id_mirror"] == audio["playback_id"]
    assert slice_doc["schema"] == "showroom_lens_media_thin_slice_v1"
    assert slice_doc["lens_video_observability_v1"]["non_gating"] is True
