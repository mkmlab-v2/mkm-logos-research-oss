#!/usr/bin/env python3
"""Zone A video bed — oracle sphere pulse (PIL raster + ffmpeg zoompan; RTMP-safe)."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "reports" / "video" / "oracle_sphere_idle_loop_latest.mp4"
DEFAULT_PNG = ROOT / "reports" / "video" / "oracle_sphere_base_latest.png"


def _render_sphere_png(path: Path, *, width: int, height: int) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (width, height), (8, 18, 36))
    draw = ImageDraw.Draw(im)
    cx, cy = width // 2, height // 2
    max_r = int(min(width, height) * 0.36)
    for r in range(max_r, 0, -3):
        t = 1.0 - (r / max_r)
        color = (
            int(25 + 200 * (t**1.6)),
            int(55 + 170 * (t**1.5)),
            int(110 + 220 * (t**1.4)),
        )
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    # Outer ring
    draw.ellipse(
        (cx - max_r - 6, cy - max_r - 6, cx + max_r + 6, cy + max_r + 6),
        outline=(90, 150, 220),
        width=3,
    )
    im = im.filter(ImageFilter.GaussianBlur(radius=1.2))
    # Re-draw bright core after soft blur
    draw2 = ImageDraw.Draw(im)
    core = int(max_r * 0.22)
    draw2.ellipse((cx - core, cy - core, cx + core, cy + core), fill=(220, 240, 255))
    im.save(path, format="PNG")


def _build_mp4_from_png(
    png: Path,
    out_mp4: Path,
    *,
    width: int,
    height: int,
    seconds: int,
    fps: int,
) -> subprocess.CompletedProcess[str]:
    sec = max(30, min(600, int(seconds)))
    frames = sec * fps
    vf = (
        f"scale={width}:{height}:flags=lanczos,"
        f"zoompan=z='1+0.035*sin(2*PI*on/{max(fps * 8, 1)})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={width}x{height}:d={frames}:fps={fps},"
        "eq=brightness=0.04:contrast=1.1:saturation=1.18,"
        "format=yuv420p"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(png),
        "-vf",
        vf,
        "-t",
        str(sec),
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build oracle_sphere_idle MP4 bed.")
    ap.add_argument("--out-mp4", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--base-png", type=Path, default=DEFAULT_PNG)
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument(
        "--live-prep",
        action="store_true",
        help="1080p · 120s loop — YouTube live visual baseline (default style: premium)",
    )
    ap.add_argument(
        "--style",
        choices=("classic", "premium"),
        default="",
        help="premium = mesh + glass UI PNG; live-prep defaults to premium",
    )
    args = ap.parse_args()

    if args.live_prep:
        args.width = 1920
        args.height = 1080
        args.seconds = max(args.seconds, 120)
    style = args.style or ("premium" if args.live_prep else "classic")

    out = args.out_mp4 if args.out_mp4.is_absolute() else ROOT / args.out_mp4
    png = args.base_png if args.base_png.is_absolute() else ROOT / args.base_png
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        if style == "premium":
            from scripts.zone_a_broadcast_visual_premium_v1 import (
                BG_BASE,
                UI_OVERLAY,
                build_motion_mp4,
                render_mesh_background,
                render_ui_overlay,
            )

            bg_png = BG_BASE if BG_BASE.is_absolute() else ROOT / BG_BASE
            ui_png = UI_OVERLAY if UI_OVERLAY.is_absolute() else ROOT / UI_OVERLAY
            render_mesh_background(bg_png, width=args.width, height=args.height)
            render_ui_overlay(ui_png, width=args.width, height=args.height)
            proc = build_motion_mp4(
                bg_png,
                out,
                width=args.width,
                height=args.height,
                seconds=args.seconds,
                fps=args.fps,
            )
            base_ref = bg_png.relative_to(ROOT).as_posix()
            ui_ref = ui_png.relative_to(ROOT).as_posix()
            renderer = "premium_mesh_ui_v2"
        else:
            _render_sphere_png(png, width=args.width, height=args.height)
            proc = _build_mp4_from_png(
                png,
                out,
                width=args.width,
                height=args.height,
                seconds=args.seconds,
                fps=args.fps,
            )
            base_ref = png.relative_to(ROOT).as_posix()
            ui_ref = None
            renderer = "pil_zoompan_v2"
    except ImportError:
        print("FAIL: Pillow required — pip install Pillow", file=sys.stderr)
        return 1

    if proc.returncode != 0 or not out.is_file():
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode or 1

    meta = {
        "schema": "oracle_sphere_idle_video_bed_v1",
        "ok": True,
        "path": out.relative_to(ROOT).as_posix(),
        "base_png": base_ref,
        "ui_overlay_png": ui_ref,
        "seconds": args.seconds,
        "size": f"{args.width}x{args.height}",
        "renderer": renderer,
        "style": style,
        "live_prep": bool(args.live_prep),
    }
    meta_path = out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
