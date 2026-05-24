"""Zone A RTMP ffmpeg one-liner emitter (no live push)."""

from __future__ import annotations

from pathlib import Path

from scripts.emit_ambient_stream_rtmp_command_v1 import build_command


def test_build_rtmp_command_fifo_concat_profile(tmp_path: Path) -> None:
    manifest = {
        "caption_config": {"disclaimer_text_ko": "본 방송은 투자·진료 조언이 아닙니다."},
        "brand_overlay": {"title_ko": "MKM Oracle Sphere", "subtitle_ko": "관측·참고용"},
    }
    playlist = tmp_path / "fifo.txt"
    playlist.write_text("file 'reports/audio/bed.wav'\n", encoding="utf-8")
    video = tmp_path / "oracle.mp4"
    video.write_bytes(b"\0" * 8)
    cmd = build_command(
        manifest,
        playlist_txt=playlist,
        video_mp4=video,
        rtmp_url="rtmp://a.rtmp.youtube.com/live2/secret-key",
        profile="fifo_concat",
    )
    assert "ffmpeg" in cmd
    assert "concat" in cmd
    assert "drawtext" in cmd
    assert "-shortest" in cmd
    assert "libx264" in cmd
    assert "flv" in cmd


def test_build_rtmp_command_ambient_24h_loops_bed(tmp_path: Path) -> None:
    manifest = {
        "caption_config": {"disclaimer_text_ko": "면책 문구 테스트"},
        "brand_overlay": {"title_ko": "MKM", "subtitle_ko": "LIVE"},
    }
    video = tmp_path / "oracle.mp4"
    video.write_bytes(b"\0" * 8)
    bed = tmp_path / "bed.wav"
    bed.write_bytes(b"RIFF" + b"\0" * 20)
    missing_ui = tmp_path / "missing_ui_overlay.png"
    cmd = build_command(
        manifest,
        playlist_txt=tmp_path / "unused.txt",
        video_mp4=video,
        rtmp_url="rtmp://a.rtmp.youtube.com/live2/key",
        profile="ambient_24h",
        bed_wav=bed,
        ui_overlay=missing_ui,
    )
    assert "stream_loop -1" in cmd
    assert str(bed.resolve()) in cmd
    assert "-shortest" not in cmd
    assert "drawtext" in cmd
    assert "malgunbd.ttf" in cmd or "fontfile=" in cmd
    assert "C\\\\:/Windows" in cmd or "C\\:/Windows" in cmd


def test_build_rtmp_command_ambient_24h_premium_png_overlay(tmp_path: Path) -> None:
    from PIL import Image

    manifest = {
        "caption_config": {"disclaimer_text_ko": "면책"},
        "brand_overlay": {"title_ko": "MKM", "subtitle_ko": "LIVE"},
    }
    video = tmp_path / "oracle.mp4"
    video.write_bytes(b"\0" * 8)
    bed = tmp_path / "bed.wav"
    bed.write_bytes(b"RIFF" + b"\0" * 20)
    ui = tmp_path / "ui.png"
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(ui)
    cmd = build_command(
        manifest,
        playlist_txt=tmp_path / "unused.txt",
        video_mp4=video,
        rtmp_url="rtmp://a.rtmp.youtube.com/live2/key",
        profile="ambient_24h",
        bed_wav=bed,
        ui_overlay=ui,
    )
    assert "overlay=0:0" in cmd
    assert "filter_complex" in cmd
    assert "drawtext" not in cmd
    assert str(ui.resolve()) in cmd
