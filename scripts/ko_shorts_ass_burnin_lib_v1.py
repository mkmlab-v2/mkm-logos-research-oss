#!/usr/bin/env python3
"""YouTube Shorts ASS safe-area + ffmpeg burn-in [HYPO]."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scripts.ko_shorts_stt_timing_lib_v1 import format_srt_v1
from scripts.media_stt_transcription_lib_v1 import parse_timestamp_seconds, wav_duration_sec

# 9:16 Shorts canvas — bottom safe band avoids like/comment UI
DEFAULT_PLAY_RES = (1080, 1920)
DEFAULT_MARGIN_L = 80
DEFAULT_MARGIN_R = 80
DEFAULT_MARGIN_V = 220
DEFAULT_FONT_SIZE = 46
DEFAULT_FONT = "Malgun Gothic"
DEFAULT_OUTLINE = 2
DEFAULT_SHADOW = 1

ASS_STYLE_PRESETS: dict[str, dict[str, int | str]] = {
    "shorts_v28": {
        "font_size": 46,
        "margin_v": 220,
        "margin_l": 80,
        "margin_r": 80,
        "font_name": DEFAULT_FONT,
        "outline": DEFAULT_OUTLINE,
        "shadow": DEFAULT_SHADOW,
        "bold": 0,
        "scale_y": 100,
        "title": "MKM ko shorts safe-area v1 (28 CPL)",
    },
    "netflix_v16": {
        "font_size": 42,
        "margin_v": 250,
        "margin_l": 90,
        "margin_r": 90,
        "font_name": DEFAULT_FONT,
        "outline": DEFAULT_OUTLINE,
        "shadow": DEFAULT_SHADOW,
        "bold": 0,
        "scale_y": 100,
        "title": "MKM ko shorts safe-area v1 (Netflix 16 CPL)",
    },
    "netflix_v16_pro": {
        "font_size": 44,
        "margin_v": 268,
        "margin_l": 96,
        "margin_r": 96,
        "font_name": DEFAULT_FONT,
        "outline": 3,
        "shadow": 2,
        "bold": 1,
        "scale_y": 104,
        "title": "MKM ko shorts Netflix pro typography v1 (16 CPL)",
    },
}


def ass_style_key_for_profile_v1(profile_key: str) -> str:
    if profile_key == "netflix_v16_pro":
        return "netflix_v16_pro"
    if profile_key == "netflix_v16":
        return "netflix_v16"
    return "shorts_v28"


def resolve_ass_style_for_profile_v1(
    profile_key: str,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Tune font/margins for profile + longest cue line."""
    style_key = ass_style_key_for_profile_v1(profile_key)
    preset = dict(ASS_STYLE_PRESETS.get(style_key, ASS_STYLE_PRESETS["shorts_v28"]))
    char_lens = [len(str(s.get("text") or "").strip()) for s in segments if str(s.get("text") or "").strip()]
    max_line = max(char_lens) if char_lens else 0
    cue_count = len(char_lens)
    font_size = int(preset.get("font_size") or DEFAULT_FONT_SIZE)
    gate_key = "netflix_v16" if profile_key in ("netflix_v16", "netflix_v16_pro") else profile_key
    if gate_key == "netflix_v16":
        if max_line <= 10:
            font_size = int(preset.get("font_size") or 42) + (2 if profile_key == "netflix_v16_pro" else 0)
        elif max_line >= 15:
            font_size = 38 if profile_key == "netflix_v16" else 40
        else:
            font_size = 42 if profile_key == "netflix_v16" else 44
        if cue_count >= 12:
            font_size = max(36 if profile_key == "netflix_v16" else 38, font_size - 2)
    preset["font_size"] = font_size
    preset["title"] = str(preset.get("title") or f"MKM {profile_key}")
    preset["ass_style_key"] = style_key
    return preset


def seconds_to_ass_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass_text(text: str) -> str:
    return str(text or "").replace("\n", "\\N").replace("{", "(").replace("}", ")")


def build_ass_v1(
    segments: list[dict[str, Any]],
    *,
    play_res_x: int = DEFAULT_PLAY_RES[0],
    play_res_y: int = DEFAULT_PLAY_RES[1],
    margin_l: int = DEFAULT_MARGIN_L,
    margin_r: int = DEFAULT_MARGIN_R,
    margin_v: int = DEFAULT_MARGIN_V,
    font_name: str = DEFAULT_FONT,
    font_size: int = DEFAULT_FONT_SIZE,
    outline: int = DEFAULT_OUTLINE,
    shadow: int = DEFAULT_SHADOW,
    bold: int = 0,
    scale_y: int = 100,
    title: str = "MKM ko shorts safe-area v1",
) -> str:
    style = (
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,"
        f"{int(bold)},0,0,0,100,{int(scale_y)},0,0,1,{int(outline)},{int(shadow)},2,"
        f"{margin_l},{margin_r},{margin_v},1"
    )
    lines = [
        "[Script Info]",
        f"Title: {title}",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {play_res_x}",
        f"PlayResY: {play_res_y}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for seg in segments:
        start = seconds_to_ass_ts(parse_timestamp_seconds(str(seg.get("start") or "00:00:00.00")))
        end = seconds_to_ass_ts(parse_timestamp_seconds(str(seg.get("end") or "00:00:00.00")))
        text = escape_ass_text(str(seg.get("text") or "").strip())
        if not text:
            continue
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return "\n".join(lines).strip() + "\n"


def burn_ass_into_vertical_video_v1(
    *,
    wav_path: Path,
    ass_path: Path,
    out_mp4: Path,
    play_res_x: int = DEFAULT_PLAY_RES[0],
    play_res_y: int = DEFAULT_PLAY_RES[1],
) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")
    duration = max(1.0, wav_duration_sec(wav_path))
    ass_posix = ass_path.resolve().as_posix().replace(":", r"\:")
    vf = f"ass='{ass_posix}'"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={play_res_x}x{play_res_y}:d={duration:.3f}",
        "-i",
        str(wav_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def segments_from_srt_v1(srt_text: str) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    segments: list[dict[str, Any]] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue
        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1],
        )
        if not m:
            continue
        start = _srt_ts_to_hms(m.group(1))
        end = _srt_ts_to_hms(m.group(2))
        text = " ".join(lines[2:])
        segments.append({"start": start, "end": end, "text": text})
    return segments


def _srt_ts_to_hms(ts: str) -> str:
    ts = ts.strip().replace(",", ".")
    return ts if re.match(r"\d{2}:\d{2}:\d{2}\.\d+", ts) else "00:00:00.00"


def write_sidecars_from_segments_v1(
    segments: list[dict[str, Any]],
    *,
    ass_path: Path,
    srt_path: Path | None = None,
    profile_key: str = "shorts_v28",
) -> None:
    style = resolve_ass_style_for_profile_v1(profile_key, segments)
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(
        build_ass_v1(
            segments,
            margin_l=int(style.get("margin_l") or DEFAULT_MARGIN_L),
            margin_r=int(style.get("margin_r") or DEFAULT_MARGIN_R),
            margin_v=int(style.get("margin_v") or DEFAULT_MARGIN_V),
            font_name=str(style.get("font_name") or DEFAULT_FONT),
            font_size=int(style.get("font_size") or DEFAULT_FONT_SIZE),
            outline=int(style.get("outline") or DEFAULT_OUTLINE),
            shadow=int(style.get("shadow") or DEFAULT_SHADOW),
            bold=int(style.get("bold") or 0),
            scale_y=int(style.get("scale_y") or 100),
            title=str(style.get("title") or "MKM ko shorts safe-area v1"),
        ),
        encoding="utf-8-sig",
    )
    if srt_path is not None:
        srt_path.write_text(format_srt_v1(segments), encoding="utf-8")
