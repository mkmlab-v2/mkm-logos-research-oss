"""FIFO → manifest → RTMP command chain (offline, no ffmpeg binary required)."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_ambient_stream_manifest_v1 as amb
import scripts.emit_ambient_stream_rtmp_command_v1 as rtmp
import scripts.manage_ambient_playlist_fifo_v1 as fifo


def test_zone_a_pipeline_fifo_manifest_rtmp(tmp_path: Path) -> None:
    root = tmp_path
    bed = root / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav"
    bed.parent.mkdir(parents=True, exist_ok=True)
    bed.write_bytes(b"RIFF" + b"\0" * 120)

    event = root / "reports" / "radio_dialogue_merged_latest.mp3"
    event.parent.mkdir(parents=True, exist_ok=True)
    event.write_bytes(b"\0" * 80)

    video = root / "reports" / "video" / "oracle_sphere_idle_loop_latest.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"\0" * 16)

    playlist_txt = root / "reports" / "ambient_stream_playlist_fifo.txt"
    state = fifo.init_fifo(root, bed, playlist_path=playlist_txt)
    state = fifo.append_event(
        root, event, kind="zone_b_morning", playlist_path=playlist_txt, state=state
    )
    assert len(state["entries"]) == 2
    assert playlist_txt.read_text(encoding="utf-8").count("file '") == 2

    manifest = amb.build_manifest(root, bed_wav=bed)
    assert manifest["visual_config"]["fifo_playlist_path"] == "reports/ambient_stream_playlist_fifo.txt"
    assert manifest["caption_config"]["disclaimer_text_ko"]

    cmd = rtmp.build_command(
        manifest,
        playlist_txt=playlist_txt,
        video_mp4=video,
        rtmp_url="rtmp://example/live/test",
        profile="ambient_24h",
        bed_wav=bed,
    )
    assert "drawtext" in cmd
    assert "stream_loop -1" in cmd
    assert "-shortest" not in cmd

    out_txt = root / "reports" / "ambient_stream_rtmp_command_latest.txt"
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(cmd + "\n", encoding="utf-8")
    summary = {
        "schema": "ambient_zone_a_pipeline_chain_smoke_v1",
        "fifo_entries": len(state["entries"]),
        "manifest_id": manifest["manifest_id"],
        "rtmp_cmd_len": len(cmd),
    }
    summary_path = root / "reports" / "ambient_zone_a_pipeline_chain_smoke_latest.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert summary["fifo_entries"] == 2
