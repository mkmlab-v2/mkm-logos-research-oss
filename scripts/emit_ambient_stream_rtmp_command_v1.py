#!/usr/bin/env python3
"""Emit full Zone A RTMP ffmpeg command (static video + audio + burn-in overlays)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports" / "ambient_stream_manifest_latest.json"
DEFAULT_PLAYLIST = ROOT / "reports" / "ambient_stream_playlist_fifo.txt"
DEFAULT_OUT = ROOT / "reports" / "ambient_stream_rtmp_command_latest.txt"
DEFAULT_BED = ROOT / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav"
UI_OVERLAY = ROOT / "reports" / "video" / "zone_a_ui_overlay_latest.png"
# Windows: bare C:/ in -vf breaks parsing; use escaped drive colon (see drawtext probe).
FONT_DRAW = r"fontfile=C\\:/Windows/Fonts/malgunbd.ttf"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _esc_drawtext(text: str, *, max_len: int = 140) -> str:
    t = (text or "")[:max_len]
    return (
        t.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("@", "\\@")
    )


def _fontcolor(expr: str) -> str:
    """Comma-separated -vf chains treat '@' as special; escape alpha syntax."""
    return expr.replace("@", "\\@")


def build_vf_filter(manifest: Dict[str, Any]) -> str:
    overlay = manifest.get("brand_overlay") or {}
    cap = manifest.get("caption_config") or {}
    disclaimer = (
        cap.get("disclaimer_burn_in_ko")
        or "투자·의료·법률 자문 아님  |  관측·참고용 (실전 판단은 청취자)"
    )
    title = _esc_drawtext(str(overlay.get("title_ko") or "MKM Oracle Sphere"))
    subtitle = _esc_drawtext(str(overlay.get("subtitle_ko") or "관측·참고용 · LIVE"))
    disc = _esc_drawtext(str(disclaimer), max_len=72)
    parts = [
        (
            f"drawtext={FONT_DRAW}:text='{title}':fontsize=44:fontcolor={_fontcolor('white@0.95')}:"
            f"x=w/2-text_w/2:y=48:box=1:boxcolor={_fontcolor('0x0a1220@0.55')}:boxborderw=12"
        ),
        (
            f"drawtext={FONT_DRAW}:text='{subtitle}':fontsize=24:fontcolor={_fontcolor('0xA8C4E8@0.92')}:"
            f"x=w/2-text_w/2:y=108:box=1:boxcolor={_fontcolor('black@0.35')}:boxborderw=6"
        ),
        (
            f"drawtext={FONT_DRAW}:text='{disc}':fontsize=20:fontcolor={_fontcolor('white@0.9')}:"
            f"x=w/2-text_w/2:y=h-72:box=1:boxcolor={_fontcolor('black@0.5')}:boxborderw=8"
        ),
    ]
    return ",".join(parts)


def premium_ui_overlay_path(ui_overlay: Path | None = None) -> Path:
    p = ui_overlay or UI_OVERLAY
    return p if p.is_absolute() else ROOT / p


def uses_premium_ui_overlay(ui_overlay: Path | None = None) -> bool:
    return premium_ui_overlay_path(ui_overlay).is_file()


def build_command(
    manifest: Dict[str, Any],
    *,
    playlist_txt: Path,
    video_mp4: Path,
    rtmp_url: str,
    profile: str = "ambient_24h",
    bed_wav: Path | None = None,
    ui_overlay: Path | None = None,
) -> str:
    vpath = video_mp4.resolve()
    rtmp = rtmp_url.strip()
    ui = premium_ui_overlay_path(ui_overlay)
    if profile == "fifo_concat":
        vf = build_vf_filter(manifest)
        return (
            f"ffmpeg -re -stream_loop -1 -i \"{vpath}\" "
            f"-f concat -safe 0 -i \"{playlist_txt.resolve()}\" "
            f"-vf \"{vf}\" -c:v libx264 -preset veryfast -pix_fmt yuv420p "
            f"-c:a aac -b:a 128k -shortest -f flv \"{rtmp}\""
        )
    bed = (bed_wav or DEFAULT_BED).resolve()
    if uses_premium_ui_overlay(ui):
        uip = ui.resolve()
        return (
            f"ffmpeg -re -stream_loop -1 -i \"{vpath}\" "
            f"-re -stream_loop -1 -i \"{bed}\" "
            f"-loop 1 -i \"{uip}\" "
            f"-filter_complex \"[0:v][2:v]overlay=0:0:format=auto,format=yuv420p[v]\" "
            f"-map \"[v]\" -map 1:a "
            f"-c:v libx264 -preset veryfast -pix_fmt yuv420p "
            f"-c:a aac -b:a 160k -ar 44100 "
            f"-f flv \"{rtmp}\""
        )
    vf = build_vf_filter(manifest)
    return (
        f"ffmpeg -re -stream_loop -1 -i \"{vpath}\" "
        f"-re -stream_loop -1 -i \"{bed}\" "
        f"-vf \"{vf}\" -map 0:v -map 1:a "
        f"-c:v libx264 -preset veryfast -pix_fmt yuv420p "
        f"-c:a aac -b:a 160k -ar 44100 "
        f"-f flv \"{rtmp}\""
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit Zone A RTMP ffmpeg one-liner.")
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--playlist-txt", type=Path, default=DEFAULT_PLAYLIST)
    ap.add_argument("--video-mp4", type=Path, default=ROOT / "reports" / "video" / "oracle_sphere_idle_loop_latest.mp4")
    ap.add_argument("--bed-wav", type=Path, default=DEFAULT_BED)
    ap.add_argument(
        "--profile",
        choices=("ambient_24h", "fifo_concat"),
        default="ambient_24h",
        help="ambient_24h = loop bed (24h); fifo_concat = concat playlist + -shortest (demo)",
    )
    ap.add_argument("--rtmp-url", type=str, default="")
    ap.add_argument("--out-txt", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    manifest_path = args.manifest_json if args.manifest_json.is_absolute() else ROOT / args.manifest_json
    manifest = _read_json(manifest_path)
    playlist = args.playlist_txt if args.playlist_txt.is_absolute() else ROOT / args.playlist_txt
    video = args.video_mp4 if args.video_mp4.is_absolute() else ROOT / args.video_mp4
    bed = args.bed_wav if args.bed_wav.is_absolute() else ROOT / args.bed_wav
    rtmp = (args.rtmp_url or os.environ.get("YOUTUBE_RTMP_URL") or "").strip()
    if not rtmp:
        cmd = "# Set YOUTUBE_RTMP_URL or --rtmp-url\n# " + build_command(
            manifest,
            playlist_txt=playlist,
            video_mp4=video,
            rtmp_url="<RTMP_URL>",
            profile=args.profile,
            bed_wav=bed,
        )
    else:
        cmd = build_command(
            manifest,
            playlist_txt=playlist,
            video_mp4=video,
            rtmp_url=rtmp,
            profile=args.profile,
            bed_wav=bed,
        )

    if args.stdout_only:
        print(cmd)
        return 0
    out = args.out_txt if args.out_txt.is_absolute() else ROOT / args.out_txt
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cmd + "\n", encoding="utf-8")
    meta = {
        "schema": "ambient_stream_rtmp_command_meta_v1",
        "profile": args.profile,
        "rtmp_configured": bool(rtmp),
        "overlay_mode": "premium_png" if uses_premium_ui_overlay() else "drawtext",
    }
    meta_path = out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
