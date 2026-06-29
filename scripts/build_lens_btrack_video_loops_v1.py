#!/usr/bin/env python3
"""Bake lens B-track video loops (4 sasang × 3 modes) via PIL + ffmpeg zoompan."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT_DIR = ROOT / "reports" / "track_c_video_hook_samples_v1"
LUT_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1.example.json"
LUT_LATEST = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"

MODE_PALETTE = {
    "idle": ((25, 55, 95), (197, 160, 87)),
    "defend": ((18, 48, 38), (255, 188, 79)),
    "attack": ((72, 28, 28), (255, 120, 90)),
}

SASANG_ACCENT = {
    "soyang": (197, 160, 87),
    "taeyang": (255, 140, 90),
    "taeeum": (120, 190, 220),
    "soeum": (186, 150, 230),
}


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _render_mode_png(path: Path, *, mode: str, sasang: str, width: int, height: int) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    bg, _default_accent = MODE_PALETTE.get(mode, MODE_PALETTE["idle"])
    accent = SASANG_ACCENT.get(sasang.strip().lower(), _default_accent)
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(im)
    cx, cy = width // 2, height // 2
    max_r = int(min(width, height) * 0.32)
    for r in range(max_r, 0, -4):
        t = 1.0 - (r / max_r)
        color = tuple(int(bg[i] + (accent[i] - bg[i]) * (t**1.4)) for i in range(3))
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    draw.ellipse((cx - max_r - 8, cy - max_r - 8, cx + max_r + 8, cy + max_r + 8), outline=accent, width=4)
    im = im.filter(ImageFilter.GaussianBlur(radius=1.0))
    draw2 = ImageDraw.Draw(im)
    core = int(max_r * 0.18)
    draw2.ellipse((cx - core, cy - core, cx + core, cy + core), fill=(240, 245, 255))
    label = f"{sasang.upper()[:2]} {mode.upper()[:6]}"
    draw2.text((12, 12), label, fill=accent)
    im.save(path, format="PNG")


def _render_animated_frame(
    *,
    frame_idx: int,
    total_frames: int,
    mode: str,
    sasang: str,
    width: int,
    height: int,
):
    from PIL import Image, ImageDraw, ImageFilter

    bg, _default_accent = MODE_PALETTE.get(mode, MODE_PALETTE["idle"])
    accent = SASANG_ACCENT.get(sasang.strip().lower(), _default_accent)
    t = frame_idx / max(1, total_frames)
    phase = t * 2.0 * math.pi

    speed = {"idle": 0.55, "defend": 0.35, "attack": 1.05}.get(mode, 0.55)
    pulse = 0.5 + 0.5 * math.sin(phase * speed)
    drift_x = int(math.sin(phase * 0.4) * width * 0.012)
    drift_y = int(math.cos(phase * 0.33) * height * 0.01)

    im = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(im)
    cx, cy = width // 2 + drift_x, height // 2 + drift_y
    max_r = int(min(width, height) * (0.28 + 0.04 * pulse))

    for ring in range(3):
        r = max_r - ring * int(max_r * 0.22)
        if r <= 8:
            continue
        mix = 0.35 + 0.25 * ring
        for step in range(r, 0, -3):
            tt = step / max(1, r)
            color = tuple(
                int(bg[i] + (accent[i] - bg[i]) * (mix * (1.0 - tt**1.2) + pulse * 0.15))
                for i in range(3)
            )
            draw.ellipse((cx - step, cy - step, cx + step, cy + step), fill=color)

    orbit_r = int(max_r * (1.05 + 0.08 * pulse))
    for k in range(5):
        ang = phase * speed * 1.4 + k * (2.0 * math.pi / 5.0)
        px = cx + int(math.cos(ang) * orbit_r)
        py = cy + int(math.sin(ang) * orbit_r * 0.55)
        pr = 3 + (k % 2)
        draw.ellipse((px - pr, py - pr, px + pr, py + pr), fill=accent)

    draw.ellipse(
        (cx - max_r - 6, cy - max_r - 6, cx + max_r + 6, cy + max_r + 6),
        outline=accent,
        width=3,
    )
    core = int(max_r * (0.14 + 0.05 * pulse))
    draw.ellipse((cx - core, cy - core, cx + core, cy + core), fill=(238, 242, 252))

    if mode == "defend":
        shield = int(max_r * 1.15)
        draw.arc(
            (cx - shield, cy - shield, cx + shield, cy + shield),
            start=200 + int(20 * math.sin(phase)),
            end=340 + int(20 * math.sin(phase)),
            fill=accent,
            width=4,
        )
    elif mode == "attack":
        for streak in range(4):
            ang = phase * 2.2 + streak * 1.2
            x2 = cx + int(math.cos(ang) * max_r * 1.35)
            y2 = cy + int(math.sin(ang) * max_r * 0.75)
            draw.line((cx, cy, x2, y2), fill=accent, width=2)

    im = im.filter(ImageFilter.GaussianBlur(radius=0.6))
    draw2 = ImageDraw.Draw(im)
    label = f"{sasang.upper()[:2]} · {mode.upper()}"
    draw2.text((14, 14), label, fill=accent)
    return im


def _build_webm_from_frames(
    frame_dir: Path,
    out_webm: Path,
    *,
    width: int,
    height: int,
    fps: int,
    bitrate_k: int = 1800,
) -> subprocess.CompletedProcess[str]:
    pattern = str(frame_dir / "frame_%04d.png")
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        pattern,
        "-an",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        f"{bitrate_k}k",
        "-pix_fmt",
        "yuv420p",
        str(out_webm),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _build_webm_from_png(
    png: Path,
    out_webm: Path,
    *,
    width: int,
    height: int,
    seconds: int,
    fps: int,
) -> subprocess.CompletedProcess[str]:
    sec = max(8, min(30, int(seconds)))
    frames = sec * fps
    vf = (
        f"scale={width}:{height}:flags=lanczos,"
        f"zoompan=z='min(zoom+0.0015,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(png),
        "-t",
        str(sec),
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "800k",
        "-pix_fmt",
        "yuv420p",
        str(out_webm),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _lut_rows() -> list[tuple[str, str, str, str]]:
    lut = {}
    if LUT_LATEST.is_file():
        lut = json.loads(LUT_LATEST.read_text(encoding="utf-8"))
    elif LUT_EXAMPLE.is_file():
        lut = json.loads(LUT_EXAMPLE.read_text(encoding="utf-8"))
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    rows: list[tuple[str, str, str, str]] = []
    for vid, row in entries.items():
        if not isinstance(row, dict):
            continue
        mode = str(row.get("showroom_display_mode") or "idle").lower()
        sasang = str(row.get("sasang_primary") or "soyang").lower()
        fname = str(row.get("file") or "")
        if fname:
            rows.append((str(vid), mode, sasang, fname))
    if not rows:
        rows = [
            ("LV_HP050_SOYANG_IDLE_V1", "idle", "soyang", "lv_hp050_soyang_idle_v1.webm"),
            ("LV_HP050_SOYANG_DEFEND_V1", "defend", "soyang", "lv_hp050_soyang_defend_v1.webm"),
            ("LV_HP050_TAEYANG_ATTACK_V1", "attack", "taeyang", "lv_hp050_taeyang_attack_v1.webm"),
        ]
    return rows


def _patch_video_lut_from_bake(
    out_dir: Path, *, width: int, height: int, fps: int, renderer: str
) -> None:
    if not LUT_LATEST.is_file():
        return
    lut = json.loads(LUT_LATEST.read_text(encoding="utf-8"))
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    for _vid, row in entries.items():
        if not isinstance(row, dict):
            continue
        fname = str(row.get("file") or "")
        stem = Path(fname).stem
        poster = out_dir / f"{stem}_poster.png"
        if poster.is_file():
            row["poster_file"] = poster.name
        row["width"] = width
        row["height"] = height
        row["fps"] = fps
        mp4 = out_dir / f"{stem}.mp4"
        if mp4.is_file():
            row["mp4_file"] = mp4.name
    lut["video_renderer"] = renderer
    lut["bake_out_dir"] = str(out_dir.relative_to(ROOT)).replace("\\", "/")
    LUT_LATEST.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Bake lens B-track video loop samples (FFmpeg)")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--seconds", type=int, default=12)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-ffmpeg", action="store_true", help="Write PNG previews only")
    p.add_argument(
        "--renderer",
        choices=("animated", "static", "pixel_v2"),
        default="pixel_v2",
        help="pixel_v2=nearest-neighbor pixel art loop (default); animated=gradient v2; static=zoompan",
    )
    p.add_argument("--only-sasang", default="", help="Filter matrix to one sasang (e.g. taeyang)")
    p.add_argument("--only-mode", default="", help="Filter matrix to one mode (idle|defend|attack)")
    args = p.parse_args()

    if not _ffmpeg_available() and not args.skip_ffmpeg and not args.dry_run:
        print("[lens-video-bake] ffmpeg not found; use --skip-ffmpeg or install ffmpeg", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "lens_btrack_video_bake_report_v1",
        "generated_at_utc": _utc_now_z(),
        "out_dir": str(args.out_dir),
        "renderer": args.renderer,
        "clips": [],
    }

    lut_rows = _lut_rows()
    if args.only_sasang:
        lut_rows = [r for r in lut_rows if r[2] == args.only_sasang.strip().lower()]
    if args.only_mode:
        lut_rows = [r for r in lut_rows if r[1] == args.only_mode.strip().lower()]
    if not lut_rows:
        print("[lens-video-bake] no LUT rows after filter", file=sys.stderr)
        return 2

    for vid, mode, sasang, fname in lut_rows:
        png = args.out_dir / f"{Path(fname).stem}_base.png"
        poster = args.out_dir / f"{Path(fname).stem}_poster.png"
        webm = args.out_dir / fname
        clip: dict[str, Any] = {
            "video_playback_id": vid,
            "mode": mode,
            "sasang_primary": sasang,
            "file": fname,
            "png": str(png),
            "poster_file": poster.name,
        }
        if args.dry_run:
            clip["status"] = "dry_run"
            report["clips"].append(clip)
            continue

        total_frames = max(8, int(args.seconds * args.fps))
        if args.renderer in ("animated", "pixel_v2"):
            if args.renderer == "pixel_v2":
                from scripts.video.lens_pixel_loop_renderer_v1 import render_pixel_animated_frame

                def _frame_fn(fi: int, n: int):
                    return render_pixel_animated_frame(
                        frame_idx=fi,
                        total_frames=n,
                        mode=mode,
                        sasang=sasang,
                        width=args.width,
                        height=args.height,
                    )
            else:

                def _frame_fn(fi: int, n: int):
                    return _render_animated_frame(
                        frame_idx=fi,
                        total_frames=n,
                        mode=mode,
                        sasang=sasang,
                        width=args.width,
                        height=args.height,
                    )

            with tempfile.TemporaryDirectory(prefix="lens_vid_") as tmp:
                frame_dir = Path(tmp)
                for fi in range(total_frames):
                    frame = _frame_fn(fi, total_frames)
                    frame_path = frame_dir / f"frame_{fi:04d}.png"
                    frame.save(frame_path, format="PNG")
                    if fi == 0:
                        frame.save(png, format="PNG")
                        frame.save(poster, format="PNG")
                clip["png_ok"] = png.is_file()
                clip["poster_ok"] = poster.is_file()
                if args.skip_ffmpeg:
                    clip["status"] = "png_only"
                    report["clips"].append(clip)
                    continue
                proc = _build_webm_from_frames(
                    frame_dir, webm, width=args.width, height=args.height, fps=args.fps
                )
        else:
            _render_mode_png(png, mode=mode, sasang=sasang, width=args.width, height=args.height)
            shutil.copy2(png, poster)
            clip["png_ok"] = png.is_file()
            clip["poster_ok"] = poster.is_file()
            if args.skip_ffmpeg:
                clip["status"] = "png_only"
                report["clips"].append(clip)
                continue
            proc = _build_webm_from_png(
                png, webm, width=args.width, height=args.height, seconds=args.seconds, fps=args.fps
            )

        clip["ffmpeg_exit"] = proc.returncode
        clip["webm_ok"] = webm.is_file() and webm.stat().st_size > 0
        clip["status"] = "ok" if clip["webm_ok"] else "fail"
        if proc.returncode != 0:
            clip["ffmpeg_stderr_tail"] = (proc.stderr or "")[-500:]
        report["clips"].append(clip)
        print(f"[lens-video-bake] {vid} -> {webm.name} renderer={args.renderer} exit={proc.returncode}")

    report_path = args.out_dir / "lens_btrack_video_bake_report_v1_latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-video-bake] WROTE: {report_path}")

    if not args.dry_run and not args.skip_ffmpeg:
        renderer_lut = "pixel_v2" if args.renderer == "pixel_v2" else "animated_v2"
        _patch_video_lut_from_bake(
            args.out_dir,
            width=args.width,
            height=args.height,
            fps=args.fps,
            renderer=renderer_lut,
        )

    failed = [c for c in report["clips"] if c.get("status") == "fail"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
