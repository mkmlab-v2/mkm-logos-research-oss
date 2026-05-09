#!/usr/bin/env python3
"""S2 preset v2 one-click renderer for presentation videos.

Folder convention (input-dir):
  clips/           -> source video clips (*.mp4, *.mov, *.mkv)
  audio/narration.wav (optional)
  audio/bgm.wav      (optional)
  audio/sfx.wav      (optional, short transition bed — mixed quietly under main audio)
  subtitles/main.ass (optional, preferred) or main.srt
  overlays/logo.png  (optional)

Output:
  output/final_s2_preset_v2.mp4
  output/final_s2_preset_v2_report.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".webm"}

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Inputs:
    clips: list[Path]
    narration: Path | None
    bgm: Path | None
    sfx: Path | None
    subtitle: Path | None
    logo: Path | None


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def ensure_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        raise RuntimeError(f"Missing required tools in PATH: {', '.join(missing)}")


def collect_inputs(input_dir: Path) -> Inputs:
    clips_dir = input_dir / "clips"
    audio_dir = input_dir / "audio"
    subs_dir = input_dir / "subtitles"
    overlays_dir = input_dir / "overlays"

    clips = sorted([p for p in clips_dir.glob("*") if p.suffix.lower() in VIDEO_EXTS and p.is_file()])
    narration = (audio_dir / "narration.wav") if (audio_dir / "narration.wav").is_file() else None
    bgm = (audio_dir / "bgm.wav") if (audio_dir / "bgm.wav").is_file() else None
    sfx = (audio_dir / "sfx.wav") if (audio_dir / "sfx.wav").is_file() else None
    sub_ass = subs_dir / "main.ass"
    sub_srt = subs_dir / "main.srt"
    if sub_ass.is_file():
        subtitle = sub_ass
    elif sub_srt.is_file():
        subtitle = sub_srt
    else:
        subtitle = None
    logo = (overlays_dir / "logo.png") if (overlays_dir / "logo.png").is_file() else None
    return Inputs(clips=clips, narration=narration, bgm=bgm, sfx=sfx, subtitle=subtitle, logo=logo)


def resolve_media_file(input_dir: Path, raw: Path | str) -> Path | None:
    """Resolve LUT/subtitle asset path: absolute, then input_dir, workspace root, cwd."""
    p = Path(raw)
    if p.is_absolute():
        return p if p.is_file() else None
    for base in (input_dir, WORKSPACE_ROOT, Path.cwd()):
        cand = (base / p).resolve()
        if cand.is_file():
            return cand
    return None


def write_concat_list(clips: list[Path], path: Path) -> None:
    lines = [f"file '{c.as_posix()}'" for c in clips]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sidechaincompress_filter(render_audio: dict | None) -> str:
    sc = (render_audio or {}).get("sidechaincompress") or {}
    t = float(sc.get("threshold", 0.06))
    r = int(sc.get("ratio", 8))
    a = int(sc.get("attack_ms", sc.get("attack", 20)))
    rel = int(sc.get("release_ms", sc.get("release", 280)))
    return f"sidechaincompress=threshold={t}:ratio={r}:attack={a}:release={rel}"


def _mix_weights(render_audio: dict | None) -> dict[str, tuple[float, float]]:
    mx = (render_audio or {}).get("mix") or {}
    def pair(key: str, default: tuple[float, float]) -> tuple[float, float]:
        v = mx.get(key)
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (float(v[0]), float(v[1]))
        return default
    return {
        "duck_narr": pair("ducked_bgm_and_narr", (1.0, 1.0)),
        "bed_voice": pair("clip_bed_vs_voice_bus", (0.2, 1.0)),
        "bed_narr": pair("clip_bed_vs_narr_only", (0.2, 1.0)),
        "bed_bgm": pair("clip_bed_vs_bgm_only", (0.35, 1.0)),
    }


def build_filter_complex(
    *,
    subtitle: Path | None,
    logo: Path | None,
    logo_v_stream_index: int | None,
    lut_path: Path | None,
    letterbox: bool,
    width: int,
    height: int,
    fps: int,
    have_narration: bool,
    have_bgm: bool,
    have_sfx: bool,
    narr_a_index: int | None,
    bgm_a_index: int | None,
    sfx_a_index: int | None,
    bgm_gain_db: float,
    sfx_gain_db: float,
    sfx_mix_weight: float,
    ducking: bool,
    logo_scale_w: int,
    render_audio: dict | None = None,
) -> tuple[str, str, str]:
    """Return (filter_complex, video_label, audio_label). Stream [0] is always joined main."""
    parts: list[str] = []

    # Video base
    parts.append(
        f"[0:v]fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v0]"
    )
    v_label = "v0"

    if lut_path is not None:
        safe_lut = lut_path.as_posix().replace("'", "\\'")
        parts.append(f"[{v_label}]lut3d='{safe_lut}'[v_lut]")
        v_label = "v_lut"

    if letterbox:
        box_h = max(2, int(height * 0.12))
        parts.append(
            f"[{v_label}]drawbox=x=0:y=0:w=iw:h={box_h}:color=black@1:t=fill,"
            f"drawbox=x=0:y=ih-{box_h}:w=iw:h={box_h}:color=black@1:t=fill[v_lb]"
        )
        v_label = "v_lb"

    if subtitle is not None:
        safe_sub = subtitle.as_posix().replace(":", r"\:").replace("'", "\\'")
        parts.append(f"[{v_label}]subtitles='{safe_sub}'[v_sub]")
        v_label = "v_sub"

    if logo is not None and logo_v_stream_index is not None:
        parts.append(f"[{logo_v_stream_index}:v]scale={logo_scale_w}:-1[logo]")
        parts.append(f"[{v_label}][logo]overlay=W-w-36:H-h-36[v_logo]")
        v_label = "v_logo"

    parts.append("[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a_base]")
    a_label = "a_base"
    mw = _mix_weights(render_audio)
    scf = _sidechaincompress_filter(render_audio)
    w_dn = mw["duck_narr"]
    w_bv = mw["bed_voice"]
    w_bn = mw["bed_narr"]
    w_bb = mw["bed_bgm"]
    w_dn_s = f"{w_dn[0]} {w_dn[1]}"
    w_bv_s = f"{w_bv[0]} {w_bv[1]}"
    w_bn_s = f"{w_bn[0]} {w_bn[1]}"
    w_bb_s = f"{w_bb[0]} {w_bb[1]}"

    if have_narration and have_bgm and narr_a_index is not None and bgm_a_index is not None:
        parts.append(f"[{narr_a_index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a_narr]")
        parts.append(
            f"[{bgm_a_index}:a]volume={bgm_gain_db}dB,aformat=sample_fmts=fltp:"
            f"sample_rates=48000:channel_layouts=stereo[a_bgm]"
        )
        if ducking:
            parts.append(f"[a_bgm][a_narr]{scf}[a_duck]")
            parts.append(f"[a_duck][a_narr]amix=inputs=2:weights={w_dn_s}:normalize=0[a_mix]")
        else:
            parts.append(f"[a_bgm][a_narr]amix=inputs=2:weights={w_dn_s}:normalize=0[a_mix]")
        parts.append(f"[a_base][a_mix]amix=inputs=2:weights={w_bv_s}:normalize=0[a_out]")
        a_label = "a_out"
    elif have_narration and narr_a_index is not None:
        parts.append(f"[{narr_a_index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a_narr]")
        parts.append(f"[a_base][a_narr]amix=inputs=2:weights={w_bn_s}:normalize=0[a_out]")
        a_label = "a_out"
    elif have_bgm and bgm_a_index is not None:
        parts.append(
            f"[{bgm_a_index}:a]volume={bgm_gain_db}dB,aformat=sample_fmts=fltp:"
            f"sample_rates=48000:channel_layouts=stereo[a_bgm]"
        )
        parts.append(f"[a_base][a_bgm]amix=inputs=2:weights={w_bb_s}:normalize=0[a_out]")
        a_label = "a_out"

    if have_sfx and sfx_a_index is not None:
        sw = f"{sfx_mix_weight:.3f}".rstrip("0").rstrip(".")
        parts.append(
            f"[{sfx_a_index}:a]volume={sfx_gain_db}dB,aformat=sample_fmts=fltp:"
            f"sample_rates=48000:channel_layouts=stereo[a_sfx]"
        )
        parts.append(f"[{a_label}][a_sfx]amix=inputs=2:weights=1 {sw}:normalize=0[a_sfxmix]")
        a_label = "a_sfxmix"

    return ";".join(parts), v_label, a_label


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Render S2 preset v2 from folder inputs.")
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=None)
    ap.add_argument("--output-name", default="final_s2_preset_v2.mp4")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--letterbox", action="store_true")
    ap.add_argument("--lut-cube", type=Path, default=None)
    ap.add_argument("--bgm-gain-db", type=float, default=-12.0)
    ap.add_argument("--sfx-gain-db", type=float, default=-22.0)
    ap.add_argument("--sfx-mix-weight", type=float, default=0.28)
    ap.add_argument("--ducking", action="store_true")
    ap.add_argument("--logo-scale-w", type=int, default=220)
    ap.add_argument(
        "--audio-profile-json",
        type=Path,
        default=None,
        help="Optional JSON: sidechaincompress + mix weights (see athena_pro_audio_profile_v1.json).",
    )
    ap.add_argument(
        "--video-profile-json",
        type=Path,
        default=None,
        help="Optional JSON: lut_cube path (see athena_pro_video_profile_v1.json). CLI --lut-cube overrides.",
    )
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_tools()
    input_dir = args.input_dir.resolve()
    output_dir = (args.output_dir or (input_dir / "output")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    ins = collect_inputs(input_dir)
    if not ins.clips:
        raise RuntimeError(f"No clips found under: {input_dir / 'clips'}")

    render_audio: dict | None = None
    if args.audio_profile_json is not None:
        raw = args.audio_profile_json
        if raw.is_absolute():
            apath = raw
        else:
            cand = input_dir / raw
            apath = cand if cand.is_file() else (Path.cwd() / raw)
        if apath.is_file():
            render_audio = json.loads(apath.read_text(encoding="utf-8"))

    render_video: dict | None = None
    if args.video_profile_json is not None:
        raw_v = args.video_profile_json
        if raw_v.is_absolute():
            vpath = raw_v
        else:
            cand_v = input_dir / raw_v
            vpath = cand_v if cand_v.is_file() else (Path.cwd() / raw_v)
        if vpath.is_file():
            render_video = json.loads(vpath.read_text(encoding="utf-8"))

    lut_effective: Path | None = None
    if args.lut_cube is not None:
        lut_effective = resolve_media_file(input_dir, args.lut_cube)
        if lut_effective is None:
            raise RuntimeError(f"--lut-cube file not found: {args.lut_cube}")
    elif render_video:
        lc = render_video.get("lut_cube")
        if lc is not None and str(lc).strip():
            lut_effective = resolve_media_file(input_dir, lc)
            if lut_effective is None:
                print(f"warning: video profile lut_cube not found, skipping LUT: {lc}", flush=True)

    concat_list = output_dir / "_concat_list.txt"
    write_concat_list(ins.clips, concat_list)

    joined = output_dir / "_joined.mp4"
    concat_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        str(joined),
    ]

    ff_inputs = ["-i", str(joined)]
    idx = 1
    narr_i: int | None = None
    bgm_i: int | None = None
    sfx_i: int | None = None
    logo_i: int | None = None

    have_narr = ins.narration is not None
    have_bgm = ins.bgm is not None
    have_sfx = ins.sfx is not None

    if have_narr:
        ff_inputs += ["-i", str(ins.narration)]
        narr_i = idx
        idx += 1
    if have_bgm:
        ff_inputs += ["-i", str(ins.bgm)]
        bgm_i = idx
        idx += 1
    if have_sfx:
        ff_inputs += ["-i", str(ins.sfx)]
        sfx_i = idx
        idx += 1
    if ins.logo is not None:
        ff_inputs += ["-i", str(ins.logo)]
        logo_i = idx
        idx += 1

    filter_complex, v_label, a_label = build_filter_complex(
        subtitle=ins.subtitle,
        logo=ins.logo,
        logo_v_stream_index=logo_i,
        lut_path=lut_effective,
        letterbox=args.letterbox,
        width=args.width,
        height=args.height,
        fps=args.fps,
        have_narration=have_narr,
        have_bgm=have_bgm,
        have_sfx=have_sfx,
        narr_a_index=narr_i,
        bgm_a_index=bgm_i,
        sfx_a_index=sfx_i,
        bgm_gain_db=args.bgm_gain_db,
        sfx_gain_db=args.sfx_gain_db,
        sfx_mix_weight=args.sfx_mix_weight,
        ducking=args.ducking,
        logo_scale_w=args.logo_scale_w,
        render_audio=render_audio,
    )

    out_mp4 = output_dir / args.output_name
    render_cmd = [
        "ffmpeg",
        "-y",
        *ff_inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        f"[{v_label}]",
        "-map",
        f"[{a_label}]",
        "-c:v",
        "libx264",
        "-preset",
        args.preset,
        "-crf",
        str(args.crf),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out_mp4),
    ]

    report = {
        "schema": "s2_preset_v2_render_report",
        "generated_at_utc": now_utc(),
        "input_dir": str(input_dir),
        "inputs": {
            "clip_count": len(ins.clips),
            "clips": [str(p) for p in ins.clips],
            "narration": str(ins.narration) if ins.narration else None,
            "bgm": str(ins.bgm) if ins.bgm else None,
            "sfx": str(ins.sfx) if ins.sfx else None,
            "subtitle": str(ins.subtitle) if ins.subtitle else None,
            "logo": str(ins.logo) if ins.logo else None,
        },
        "stream_indices": {
            "narr_a": narr_i,
            "bgm_a": bgm_i,
            "sfx_a": sfx_i,
            "logo_v": logo_i,
        },
        "settings": {
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "crf": args.crf,
            "preset": args.preset,
            "letterbox": args.letterbox,
            "lut_cube_cli": str(args.lut_cube) if args.lut_cube else None,
            "lut_cube_effective": str(lut_effective) if lut_effective else None,
            "video_profile_json": str(args.video_profile_json) if args.video_profile_json else None,
            "bgm_gain_db": args.bgm_gain_db,
            "sfx_gain_db": args.sfx_gain_db,
            "sfx_mix_weight": args.sfx_mix_weight,
            "ducking": args.ducking,
            "audio_profile_json": str(args.audio_profile_json) if args.audio_profile_json else None,
        },
        "commands": {
            "concat_cmd": concat_cmd,
            "render_cmd": render_cmd,
        },
        "output_video": str(out_mp4),
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        run(concat_cmd)
        run(render_cmd)

    report_path = output_dir / "final_s2_preset_v2_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_video": str(out_mp4), "report_json": str(report_path), "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
