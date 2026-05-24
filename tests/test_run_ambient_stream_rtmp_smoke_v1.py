"""Zone A RTMP smoke — dry-run and missing-RTMP guard."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_ambient_stream_rtmp_smoke_v1 import build_smoke_argv, main


def test_build_smoke_argv_includes_duration(tmp_path: Path) -> None:
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\0" * 8)
    bed = tmp_path / "b.wav"
    bed.write_bytes(b"RIFF" + b"\0" * 20)
    manifest = {
        "caption_config": {"disclaimer_text_ko": "면책"},
        "brand_overlay": {"title_ko": "T", "subtitle_ko": "S"},
    }
    argv = build_smoke_argv(
        manifest,
        video_mp4=video,
        bed_wav=bed,
        rtmp_url="rtmp://a.rtmp.youtube.com/live2/key",
        seconds=30,
    )
    assert argv[0] == "ffmpeg"
    assert "-t" in argv
    assert "30.0" in argv or "30" in argv
    assert argv[-1].startswith("rtmp://")


def test_smoke_dry_run_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("YOUTUBE_RTMP_URL", "rtmp://a.rtmp.youtube.com/live2/key")
    root = tmp_path
    manifest = root / "reports" / "ambient_stream_manifest_latest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "playlist": [{"path": "reports/audio/mkm_ambient_bed_loop_latest.wav"}],
                "caption_config": {"disclaimer_text_ko": "면책"},
                "brand_overlay": {"title_ko": "MKM", "subtitle_ko": "LIVE"},
            }
        ),
        encoding="utf-8",
    )
    video = root / "reports/video/oracle_sphere_idle_loop_latest.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"\0" * 8)
    bed = root / "reports/audio/mkm_ambient_bed_loop_latest.wav"
    bed.parent.mkdir(parents=True)
    bed.write_bytes(b"RIFF" + b"\0" * 20)

    monkeypatch.chdir(root)
    import scripts.run_ambient_stream_rtmp_smoke_v1 as smoke_mod

    monkeypatch.setattr(smoke_mod, "ROOT", root)
    monkeypatch.setattr(smoke_mod, "DEFAULT_MANIFEST", manifest)
    monkeypatch.setattr(smoke_mod, "DEFAULT_VIDEO", video)
    monkeypatch.setattr(smoke_mod, "DEFAULT_BED", bed)

    import sys

    monkeypatch.setattr(sys, "argv", ["smoke", "--dry-run", "--stdout-only"])
    assert main() == 0
