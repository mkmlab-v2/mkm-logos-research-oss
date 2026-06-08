"""Deterministic pixel-art ambient loop frames for lens B-track showroom (cost-first v2)."""

from __future__ import annotations

import math

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

LOGICAL_W = 160
LOGICAL_H = 90

# 8-color style ramps (bg, mid, accent, hot, core, label, star, shield)
def _palette(mode: str, sasang: str) -> dict[str, tuple[int, int, int]]:
    bg, _ = MODE_PALETTE.get(mode, MODE_PALETTE["idle"])
    accent = SASANG_ACCENT.get(sasang.strip().lower(), (200, 180, 120))
    mid = tuple(int(bg[i] * 0.55 + accent[i] * 0.45) for i in range(3))
    hot = tuple(min(255, int(accent[i] * 1.08)) for i in range(3))
    core = (248, 250, 255)
    label = accent
    star = tuple(int(bg[i] + (accent[i] - bg[i]) * 0.35) for i in range(3))
    shield = tuple(min(255, int(accent[i] * 0.85 + 40)) for i in range(3))
    return {
        "bg": bg,
        "mid": mid,
        "accent": accent,
        "hot": hot,
        "core": core,
        "label": label,
        "star": star,
        "shield": shield,
    }


def _put(im, x: int, y: int, color: tuple[int, int, int], *, w: int = 1, h: int = 1) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(im)
    draw.rectangle((x, y, x + w - 1, y + h - 1), fill=color)


def _draw_stars(im, pal: dict[str, tuple[int, int, int]], *, phase: float, count: int = 28) -> None:
    w, h = im.size
    for i in range(count):
        sx = (i * 37 + 11) % w
        sy = (i * 53 + 7) % h
        blink = 0.5 + 0.5 * math.sin(phase * 1.7 + i * 0.9)
        if blink < 0.35:
            continue
        _put(im, sx, sy, pal["star"] if blink < 0.75 else pal["accent"])


def _draw_ring_pixels(
    im,
    cx: int,
    cy: int,
    radius: int,
    color: tuple[int, int, int],
    *,
    step: int = 2,
) -> None:
    w, h = im.size
    for deg in range(0, 360, step):
        rad = math.radians(deg)
        px = cx + int(math.cos(rad) * radius)
        py = cy + int(math.sin(rad) * radius * 0.62)
        if 0 <= px < w and 0 <= py < h:
            _put(im, px, py, color, w=2, h=2)


def _draw_label(im, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    """Minimal 3x5 block font (uppercase + dot)."""
    font: dict[str, list[str]] = {
        "S": ["111", "100", "111", "001", "111"],
        "O": ["111", "101", "101", "101", "111"],
        "Y": ["101", "101", "010", "010", "010"],
        "A": ["010", "101", "111", "101", "101"],
        "N": ["101", "111", "111", "111", "101"],
        "G": ["011", "100", "101", "101", "011"],
        "T": ["111", "010", "010", "010", "010"],
        "E": ["111", "100", "110", "100", "111"],
        "U": ["101", "101", "101", "101", "111"],
        "M": ["101", "111", "111", "101", "101"],
        "I": ["111", "010", "010", "010", "111"],
        "D": ["110", "101", "101", "101", "110"],
        "F": ["111", "100", "110", "100", "100"],
        "C": ["011", "100", "100", "100", "011"],
        "K": ["101", "101", "110", "101", "101"],
        "R": ["110", "101", "110", "101", "101"],
        "·": ["000", "000", "010", "000", "000"],
        " ": ["000", "000", "000", "000", "000"],
    }
    cx = x
    for ch in text.upper():
        glyph = font.get(ch, font[" "])
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == "1":
                    _put(im, cx + col_i * 2, y + row_i * 2, color, w=2, h=2)
        cx += 8


def render_pixel_logical_frame(
    *,
    frame_idx: int,
    total_frames: int,
    mode: str,
    sasang: str,
) -> "Image.Image":
    from PIL import Image

    pal = _palette(mode, sasang)
    im = Image.new("RGB", (LOGICAL_W, LOGICAL_H), pal["bg"])
    t = frame_idx / max(1, total_frames)
    phase = t * 2.0 * math.pi
    speed = {"idle": 0.55, "defend": 0.35, "attack": 1.05}.get(mode, 0.55)
    pulse = 0.5 + 0.5 * math.sin(phase * speed)

    _draw_stars(im, pal, phase=phase)

    cx, cy = LOGICAL_W // 2, LOGICAL_H // 2 + 2
    base_r = int(min(LOGICAL_W, LOGICAL_H) * (0.22 + 0.03 * pulse))

    for ring in range(3):
        r = base_r - ring * 5
        if r > 4:
            col = pal["mid"] if ring else pal["accent"]
            _draw_ring_pixels(im, cx, cy, r, col, step=3 + ring)

    for k in range(4):
        ang = phase * speed * 1.3 + k * (math.pi / 2.0)
        px = cx + int(math.cos(ang) * (base_r + 8))
        py = cy + int(math.sin(ang) * (base_r + 8) * 0.55)
        _put(im, px, py, pal["hot"], w=3, h=3)

    core = 3 + int(2 * pulse)
    _put(im, cx - core, cy - core, pal["core"], w=core * 2 + 1, h=core * 2 + 1)

    if mode == "defend":
        for deg in range(200, 341, 4):
            rad = math.radians(deg + 8 * math.sin(phase))
            px = cx + int(math.cos(rad) * (base_r + 12))
            py = cy + int(math.sin(rad) * (base_r + 12) * 0.6)
            _put(im, px, py, pal["shield"], w=2, h=2)
    elif mode == "attack":
        for streak in range(5):
            ang = phase * 2.0 + streak * 0.9
            for dist in range(4, base_r + 14, 3):
                px = cx + int(math.cos(ang) * dist)
                py = cy + int(math.sin(ang) * dist * 0.55)
                _put(im, px, py, pal["hot"], w=2, h=2)

    code = sasang.upper()[:2]
    mode_tag = {"idle": "IDL", "defend": "DEF", "attack": "ATK"}.get(mode, mode[:3].upper())
    _draw_label(im, f"{code}·{mode_tag}", 6, 6, pal["label"])
    return im


def render_pixel_animated_frame(
    *,
    frame_idx: int,
    total_frames: int,
    mode: str,
    sasang: str,
    width: int,
    height: int,
):
    from PIL import Image

    logical = render_pixel_logical_frame(
        frame_idx=frame_idx,
        total_frames=total_frames,
        mode=mode,
        sasang=sasang,
    )
    return logical.resize((width, height), Image.Resampling.NEAREST)


def render_pixel_poster_frame(*, mode: str, sasang: str, width: int, height: int):
    return render_pixel_animated_frame(
        frame_idx=0,
        total_frames=1,
        mode=mode,
        sasang=sasang,
        width=width,
        height=height,
    )
