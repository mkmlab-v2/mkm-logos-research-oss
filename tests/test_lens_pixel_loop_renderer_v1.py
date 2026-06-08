"""Smoke tests for deterministic pixel v2 lens loop renderer."""

from __future__ import annotations

from scripts.video.lens_pixel_loop_renderer_v1 import (
    LOGICAL_H,
    LOGICAL_W,
    render_pixel_animated_frame,
    render_pixel_logical_frame,
    render_pixel_poster_frame,
)


def test_logical_frame_size_and_mode_variation() -> None:
    idle = render_pixel_logical_frame(frame_idx=0, total_frames=30, mode="idle", sasang="taeyang")
    attack = render_pixel_logical_frame(frame_idx=0, total_frames=30, mode="attack", sasang="taeyang")
    assert idle.size == (LOGICAL_W, LOGICAL_H)
    assert attack.size == (LOGICAL_W, LOGICAL_H)
    assert idle.getpixel((0, 0)) != attack.getpixel((0, 0))


def test_upscale_nearest_and_poster() -> None:
    frame = render_pixel_animated_frame(
        frame_idx=5,
        total_frames=60,
        mode="defend",
        sasang="soeum",
        width=1280,
        height=720,
    )
    poster = render_pixel_poster_frame(mode="defend", sasang="soeum", width=1280, height=720)
    assert frame.size == (1280, 720)
    assert poster.size == (1280, 720)
