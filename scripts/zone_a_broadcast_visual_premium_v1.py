#!/usr/bin/env python3
"""Zone A broadcast visuals v2 — depth orb, starfield, minimal glass chrome (PIL)."""

from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path
from typing import Any, Tuple

ROOT = Path(__file__).resolve().parents[1]

UI_OVERLAY = ROOT / "reports" / "video" / "zone_a_ui_overlay_latest.png"
BG_BASE = ROOT / "reports" / "video" / "zone_a_bg_mesh_latest.png"

FONT_LATIN_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_LATIN = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_KO = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_KO_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


def _font(size: int, *, bold: bool = False, latin: bool = False) -> Any:
    from PIL import ImageFont

    if latin:
        candidates = [FONT_LATIN_BOLD if bold else FONT_LATIN, FONT_KO_BOLD, FONT_KO]
    else:
        candidates = [FONT_KO_BOLD if bold else FONT_KO, FONT_LATIN_BOLD, FONT_LATIN]
    for p in candidates:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _glass_panel(
    layer: Any,
    box: Tuple[int, int, int, int],
    *,
    radius: int = 18,
    fill: Tuple[int, int, int, int] = (10, 18, 32, 140),
) -> None:
    from PIL import ImageDraw

    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=radius, fill=fill)
    # Top highlight (faux glass edge)
    d.rounded_rectangle(
        (x0 + 1, y0 + 1, x1 - 1, y0 + max(3, radius // 4)),
        radius=radius,
        fill=(255, 255, 255, 28),
    )
    d.rounded_rectangle(box, radius=radius, outline=(255, 255, 255, 48), width=1)
    d.rounded_rectangle(
        (x0 + 2, y0 + 2, x1 - 2, y1 - 2),
        radius=max(4, radius - 2),
        outline=(120, 180, 255, 22),
        width=1,
    )


def _draw_starfield(layer: Any, w: int, h: int, cx: int, cy: int, orb_r: int) -> None:
    from PIL import ImageDraw

    rng = random.Random(20260523)
    d = ImageDraw.Draw(layer)
    orb_guard = (orb_r * 1.35) ** 2
    for _ in range(520):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        if (x - cx) ** 2 + (y - cy) ** 2 < orb_guard:
            continue
        a = rng.randint(35, 200)
        if rng.random() < 0.08:
            d.ellipse((x - 1, y - 1, x + 2, y + 2), fill=(200, 220, 255, a))
        else:
            layer.putpixel((x, y), (220, 230, 255, a))


def _draw_orb(layer: Any, cx: int, cy: int, r: int) -> None:
    """Layered luminous orb — no flat white disc."""
    from PIL import Image, ImageDraw, ImageFilter

    w, h = layer.size
    local = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(local)

    # Outer atmospheric glow
    for i, (rx, ry, alpha) in enumerate(
        [
            (int(r * 1.55), int(r * 1.45), 35),
            (int(r * 1.25), int(r * 1.15), 55),
            (int(r * 1.05), int(r * 0.98), 80),
        ]
    ):
        d.ellipse(
            (cx - rx, cy - ry, cx + rx, cy + ry),
            fill=(40, 100, 200, alpha),
        )

    # Body: color ramps (cyan core → deep blue edge)
    for step in range(r, 0, -3):
        t = step / r
        col = (
            int(20 + 60 * (1 - t)),
            int(90 + 110 * (1 - t**0.7)),
            int(160 + 80 * (1 - t**0.5)),
            int(25 + 200 * (1 - t) ** 2.2),
        )
        d.ellipse((cx - step, cy - step, cx + step, cy + step), fill=col)

    # Specular highlight (offset — 3D cue)
    hx, hy = cx - int(r * 0.22), cy - int(r * 0.28)
    hr = int(r * 0.35)
    for s in range(hr, 0, -2):
        u = s / hr
        d.ellipse(
            (hx - s, hy - s, hx + s, hy + s),
            fill=(200, 235, 255, int(90 * (u**1.5))),
        )

    # Inner core — soft cyan (never pure white)
    cr = int(r * 0.12)
    d.ellipse(
        (cx - cr, cy - cr, cx + cr, cy + cr),
        fill=(140, 210, 255, 200),
    )

    # Thin orbital rings
    for ri, alpha in zip(
        (r + 8, r + 22, r + 38),
        (140, 90, 50),
    ):
        d.ellipse(
            (cx - ri, cy - ri, cx + ri, cy + ri),
            outline=(160, 220, 255, alpha),
            width=2 if ri == r + 8 else 1,
        )

    # Arc ticks (12 positions)
    for i in range(12):
        ang = math.tau * i / 12
        x1 = cx + int(math.cos(ang) * (r + 14))
        y1 = cy + int(math.sin(ang) * (r + 14))
        x2 = cx + int(math.cos(ang) * (r + 28))
        y2 = cy + int(math.sin(ang) * (r + 28))
        d.line((x1, y1, x2, y2), fill=(120, 200, 255, 100), width=2)

    local = local.filter(ImageFilter.GaussianBlur(radius=1.1))
    layer.alpha_composite(local)


def _vignette(layer: Any) -> None:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    w, h = layer.size
    vig = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((int(w * 0.06), int(h * 0.05), int(w * 0.94), int(h * 0.95)), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(w, h) // 14))
    vig.putalpha(ImageChops.subtract(Image.new("L", (w, h), 155), mask))
    layer.alpha_composite(vig)


def render_mesh_background(path: Path, *, width: int, height: int) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = width, height
    cx, cy = w // 2, h // 2 + int(h * 0.02)
    r_orb = int(min(w, h) * 0.22)

    # Deep space base
    base = Image.new("RGBA", (w, h), (4, 8, 20, 255))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        for x in range(w):
            u = x / max(w - 1, 1)
            r = int(10 + 18 * (1 - t) + 10 * (0.5 - abs(u - 0.5)))
            g = int(16 + 34 * (1 - t))
            b = int(36 + 58 * (1 - t**0.8))
            px[x, y] = (r, g, b, 255)

    # Nebula blobs
    blobs = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blobs)
    for bx, by, brx, bry, col in (
        (0.22, 0.35, 0.28, 0.22, (25, 70, 160, 100)),
        (0.78, 0.28, 0.24, 0.18, (90, 40, 140, 90)),
        (0.5, 0.68, 0.32, 0.24, (15, 100, 140, 85)),
    ):
        bd.ellipse(
            (
                int(w * bx - w * brx),
                int(h * by - h * bry),
                int(w * bx + w * brx),
                int(h * by + h * bry),
            ),
            fill=col,
        )
    blobs = blobs.filter(ImageFilter.GaussianBlur(radius=48))
    comp = Image.alpha_composite(base, blobs)

    stars = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _draw_starfield(stars, w, h, cx, cy, r_orb)
    comp = Image.alpha_composite(comp, stars)

    _draw_orb(comp, cx, cy, r_orb)
    _vignette(comp)
    comp.convert("RGB").save(path, format="PNG", optimize=True)


def render_ui_overlay(
    path: Path,
    *,
    width: int,
    height: int,
    title: str = "MKM Oracle Sphere",
    subtitle: str = "관측 · 참고용",
    disclaimer: str = "투자·의료·법률 자문 아님  ·  관측·참고용  ·  실전 판단은 청취자",
) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = width, height
    ui = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Thin top chrome — does not cover the orb
    bar_h = 88
    _glass_panel(ui, (48, 36, w - 48, 36 + bar_h), radius=20, fill=(8, 14, 28, 125))

    d = ImageDraw.Draw(ui)
    # LIVE pill
    pill = (68, 52, 168, 80)
    d.rounded_rectangle(pill, radius=14, fill=(210, 48, 58, 240))
    d.ellipse((pill[0] + 12, pill[1] + 12, pill[0] + 20, pill[1] + 20), fill=(255, 255, 255, 255))
    d.text((pill[0] + 28, pill[1] + 6), "LIVE", font=_font(15, bold=True, latin=True), fill=(255, 255, 255, 255))

    title_font = _font(38, bold=True, latin=True)
    sub_font = _font(19)
    d.text((188, 50), title, font=title_font, fill=(248, 252, 255, 252))
    d.text((188, 88), subtitle, font=sub_font, fill=(140, 185, 235, 230))

    # Bottom disclaimer — slim
    bar_h2 = 48
    by0 = h - bar_h2 - 28
    _glass_panel(ui, (80, by0, w - 80, by0 + bar_h2), radius=14, fill=(6, 12, 24, 150))
    disc_font = _font(16)
    bbox = d.textbbox((0, 0), disclaimer, font=disc_font)
    tw = bbox[2] - bbox[0]
    d.text(((w - tw) // 2, by0 + 14), disclaimer, font=disc_font, fill=(210, 220, 235, 235))

    ui.save(path, format="PNG")


def build_motion_mp4(
    bg_png: Path,
    out_mp4: Path,
    *,
    width: int,
    height: int,
    seconds: int,
    fps: int = 30,
) -> subprocess.CompletedProcess[str]:
    sec = max(30, min(600, int(seconds)))
    frames = sec * fps
    period = fps * 14
    vf = (
        f"zoompan=z='1+0.012*sin(2*PI*on/{period})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={width}x{height}:d={frames}:fps={fps},"
        "eq=brightness=0.06:contrast=1.05:saturation=1.12,"
        "format=yuv420p"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(bg_png),
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
        "17",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def build_preview_mp4(
    bg_mp4: Path,
    ui_png: Path,
    bed_wav: Path,
    out_mp4: Path,
    *,
    seconds: float,
) -> subprocess.CompletedProcess[str]:
    sec = max(5.0, min(60.0, float(seconds)))
    cmd = [
        "ffmpeg",
        "-y",
        "-t",
        str(sec),
        "-i",
        str(bg_mp4),
        "-i",
        str(ui_png),
        "-i",
        str(bed_wav),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
        "-map",
        "[v]",
        "-map",
        "2:a",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "17",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        str(out_mp4),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)
