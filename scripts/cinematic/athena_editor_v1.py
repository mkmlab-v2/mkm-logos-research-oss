#!/usr/bin/env python3
"""Assemble external short clips into subtitle-burned cinematic output.

Workflow:
1) Normalize external clips to fixed duration (default 6s) and consistent video/audio format.
2) Build narration/BGM from scenario (optional ambient pad or external --bgm-file).
3) Generate subtitles from scenario (optional).
4) Optional: overlays/logo.png, audio/sfx.wav (transition bed), end-logo card.
5) Render final MP4 with render_s2_preset_v2.py and run quality gate.

Promo-oriented flags:
  --promo-pack       ambient BGM if no file + transition SFX (corner logo still needs --logo-path)
  --logo-path        PNG copied to s2 overlays/logo.png
  --transition-sfx   generated soft ticks at shot boundaries
  --end-card-sec     append MKM-style end slate (needs logo path)
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
_CIN_DIR = Path(__file__).resolve().parent
if str(_CIN_DIR) not in sys.path:
    sys.path.insert(0, str(_CIN_DIR))
from pro_audio_engine import DEFAULT_PROFILE, load_audio_profile, normalize_editor_stems, write_render_audio_snippet
from pro_video_engine import DEFAULT_VIDEO_PROFILE, load_video_profile, write_render_video_snippet

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCENARIO = ART / "cinematic_scenario_sample_v1.txt"
DEFAULT_S2_DIR = ART / "cinematic_s2_input_editor_v1"
DEFAULT_REPORT = ART / "athena_editor_v1_report_latest.json"
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def split_lines(text: str, count: int) -> list[str]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        lines = ["MKM LAB control pipeline demonstration."]
    out = []
    while len(out) < count:
        out.append(lines[len(out) % len(lines)])
    return out


def collect_source_clips(input_dir: Path, max_shots: int) -> list[Path]:
    # 1) flat mode: input_dir/*.mp4
    flat = sorted([p for p in input_dir.glob("*") if p.suffix.lower() in VIDEO_EXTS and p.is_file()])
    if flat:
        return flat[:max_shots]

    # 2) nested mode: input_dir/shot_XX/clip.mp4 (or first video in each shot dir)
    nested: list[Path] = []
    shot_dirs = sorted([d for d in input_dir.glob("shot_*") if d.is_dir()], key=lambda p: p.name)
    for d in shot_dirs:
        direct_clip = d / "clip.mp4"
        if direct_clip.is_file():
            nested.append(direct_clip)
            continue
        candidates = sorted([p for p in d.glob("*") if p.suffix.lower() in VIDEO_EXTS and p.is_file()])
        if candidates:
            nested.append(candidates[0])
    return nested[:max_shots]


def srt_ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(lines: list[str], shot_sec: int, out_path: Path) -> None:
    t = 0.0
    blocks = []
    for i, line in enumerate(lines, start=1):
        blocks.append(f"{i}\n{srt_ts(t)} --> {srt_ts(t + shot_sec)}\n{line}\n")
        t += float(shot_sec)
    out_path.write_text("\n".join(blocks), encoding="utf-8")


def write_ambient_bgm_wav(out_path: Path, duration_sec: float) -> None:
    """Generate a soft two-tone ambient pad (no external assets)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    d = max(1.0, float(duration_sec))
    fc = (
        f"sine=frequency=174:sample_rate=48000:duration={d}[s1];"
        f"sine=frequency=261:sample_rate=48000:duration={d}[s2];"
        f"[s1][s2]amix=inputs=2:normalize=0,lowpass=f=900,volume=-22dB,"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[out]"
    )
    p = run(
        [
            "ffmpeg",
            "-y",
            "-filter_complex",
            fc,
            "-map",
            "[out]",
            str(out_path),
        ]
    )
    if p.returncode != 0:
        raise RuntimeError(f"ambient BGM generation failed: {out_path}")


def write_transition_sfx_wav(out_path: Path, duration_sec: float, shot_sec: float) -> None:
    """Stereo WAV with soft ticks near each shot boundary (presentation polish)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 48000
    n_samples = int(max(0.5, duration_sec) * sample_rate)
    shot_samples = max(1, int(float(shot_sec) * sample_rate))
    tail = max(1, int(0.07 * sample_rate))
    frames: list[bytes] = []
    for i in range(n_samples):
        pos_in_shot = i % shot_samples
        amp = 0.0
        if pos_in_shot >= shot_samples - tail:
            t = i / sample_rate
            amp = 0.06 * math.sin(2 * math.pi * 1100.0 * t)
        s = int(max(-32767, min(32767, amp * 12000.0)))
        frames.append(struct.pack("<hh", s, s))
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))


def copy_or_convert_bgm_file(src: Path, dst_wav: Path) -> None:
    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".wav":
        shutil.copy2(src, dst_wav)
        return
    p = run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ar",
            "48000",
            "-ac",
            "2",
            str(dst_wav),
        ]
    )
    if p.returncode != 0:
        raise RuntimeError(f"BGM convert failed: {src}")


def append_end_logo_card(
    *,
    main_mp4: Path,
    logo_png: Path,
    out_mp4: Path,
    width: int,
    height: int,
    duration_sec: float,
    tmp_dir: Path,
) -> None:
    """Concatenate main video with a short logo end card (same audio layout)."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    slate = tmp_dir / "_end_slate.mp4"
    d = max(0.5, float(duration_sec))
    p1 = run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0f172a:s={width}x{height}:d={d}",
            "-i",
            str(logo_png),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            "[0:v][1:v]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p[v]",
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-t",
            str(d),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "128k",
            str(slate),
        ]
    )
    if p1.returncode != 0:
        raise RuntimeError("end slate encode failed")
    p2 = run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(main_mp4),
            "-i",
            str(slate),
            "-filter_complex",
            "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_mp4),
        ]
    )
    if p2.returncode != 0:
        raise RuntimeError("end card concat failed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-clips-dir", type=Path, required=True)
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--shot-sec", type=int, default=6)
    ap.add_argument("--max-shots", type=int, default=10)
    ap.add_argument("--s2-input-dir", type=Path, default=DEFAULT_S2_DIR)
    ap.add_argument("--output-name", default="final_s2_editor_v1.mp4")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--no-subtitles", action="store_true")
    ap.add_argument("--no-narration", action="store_true")
    ap.add_argument(
        "--bgm-style",
        choices=["sine", "ambient"],
        default="sine",
        help="When no --bgm-file: sine = simple tone bed; ambient = soft two-tone pad.",
    )
    ap.add_argument("--bgm-file", type=Path, default=None, help="Optional BGM file (.wav/.mp3 etc.); converted to 48k stereo WAV.")
    ap.add_argument("--logo-path", type=Path, default=None, help="Optional PNG copied to s2 overlays/logo.png for corner bug.")
    ap.add_argument("--transition-sfx", action="store_true", help="Write audio/sfx.wav (soft shot-boundary ticks) for render mix.")
    ap.add_argument("--end-card-sec", type=float, default=0.0, help="If >0, append end card with logo (requires --end-logo-path or --logo-path).")
    ap.add_argument("--end-logo-path", type=Path, default=None, help="Logo for end slate; defaults to --logo-path.")
    ap.add_argument("--promo-pack", action="store_true", help="ambient BGM (if no --bgm-file), transition SFX, corner logo when provided.")
    ap.add_argument("--render-width", type=int, default=1920)
    ap.add_argument("--render-height", type=int, default=1080)
    ap.add_argument("--sfx-gain-db", type=float, default=-22.0)
    ap.add_argument("--sfx-mix-weight", type=float, default=0.28)
    ap.add_argument(
        "--pro-audio",
        action="store_true",
        help="LUFS-normalize narration/bgm stems (profile loudnorm) and pass duck/mix JSON to render.",
    )
    ap.add_argument(
        "--pro-audio-profile",
        type=Path,
        default=None,
        help=f"JSON profile (default: {DEFAULT_PROFILE.name} under docs/final/artifacts).",
    )
    ap.add_argument(
        "--pro-video",
        action="store_true",
        help="Pass LUT/video snippet to render (default profile allows null lut_cube).",
    )
    ap.add_argument(
        "--pro-video-profile",
        type=Path,
        default=None,
        help=f"Video JSON (default: {DEFAULT_VIDEO_PROFILE.name}).",
    )
    args = ap.parse_args()

    clip_dir = args.input_clips_dir if args.input_clips_dir.is_absolute() else (ROOT / args.input_clips_dir)
    if not clip_dir.exists():
        raise RuntimeError(f"Input clips directory not found: {clip_dir}")

    source_clips = collect_source_clips(clip_dir, args.max_shots)
    if not source_clips:
        raise RuntimeError(f"No video clips found in: {clip_dir}")

    s2_dir = args.s2_input_dir if args.s2_input_dir.is_absolute() else (ROOT / args.s2_input_dir)
    clips_out = s2_dir / "clips"
    audio_out = s2_dir / "audio"
    subs_out = s2_dir / "subtitles"
    overlays_out = s2_dir / "overlays"
    clips_out.mkdir(parents=True, exist_ok=True)
    audio_out.mkdir(parents=True, exist_ok=True)
    subs_out.mkdir(parents=True, exist_ok=True)
    overlays_out.mkdir(parents=True, exist_ok=True)

    if args.promo_pack:
        args.bgm_style = "ambient"
        args.transition_sfx = True

    logo_src = args.logo_path
    if logo_src is not None:
        dst_logo = overlays_out / "logo.png"
        shutil.copy2(logo_src if logo_src.is_absolute() else (ROOT / logo_src), dst_logo)

    norm_results = []
    for i, src in enumerate(source_clips, start=1):
        dst = clips_out / f"shot_{i:02d}.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(src),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            str(args.shot_sec),
            "-vf",
            "fps=24,scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,format=yuv420p",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(dst),
        ]
        p = run(cmd)
        norm_results.append({"src": str(src), "dst": str(dst), "returncode": p.returncode, "stderr_tail": p.stderr[-400:]})
        if p.returncode != 0:
            raise RuntimeError(f"Clip normalization failed: {src}")

    scenario_text = args.scenario_file.read_text(encoding="utf-8")
    lines = split_lines(scenario_text, len(source_clips))

    srt_path = subs_out / "main.srt"
    if args.no_subtitles:
        if srt_path.exists():
            srt_path.unlink()
    else:
        write_srt(lines, args.shot_sec, srt_path)

    narr_wav = audio_out / "narration.wav"
    bgm_wav = audio_out / "bgm.wav"
    duration = len(source_clips) * args.shot_sec

    if args.no_narration:
        if narr_wav.exists():
            narr_wav.unlink()
    else:
        narr_text = audio_out / "_narration_input.txt"
        narr_text.write_text(" ".join(lines) + "\n", encoding="utf-8")
        narr_filter_path = narr_text.as_posix().replace(":", r"\:")
        tts = run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"flite=textfile='{narr_filter_path}':voice=slt",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(narr_wav),
            ]
        )
        if tts.returncode != 0:
            raise RuntimeError("TTS generation failed")

    if args.bgm_file is not None:
        src_bgm = args.bgm_file if args.bgm_file.is_absolute() else (ROOT / args.bgm_file)
        copy_or_convert_bgm_file(src_bgm, bgm_wav)
    elif args.bgm_style == "ambient":
        write_ambient_bgm_wav(bgm_wav, float(duration))
    else:
        bgm = run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=120:sample_rate=48000:duration={duration}",
                "-filter:a",
                "volume=-22dB",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(bgm_wav),
            ]
        )
        if bgm.returncode != 0:
            raise RuntimeError("BGM generation failed")

    sfx_path = audio_out / "sfx.wav"
    if args.transition_sfx:
        write_transition_sfx_wav(sfx_path, float(duration), float(args.shot_sec))
    elif sfx_path.exists():
        sfx_path.unlink()

    output_dir = s2_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    final_target = output_dir / args.output_name

    pro_audio_profile_path: Path | None = None
    pro_audio_normalized: list[str] = []
    if args.pro_audio:
        prof_path = args.pro_audio_profile
        if prof_path is None:
            prof_path = DEFAULT_PROFILE
        elif not prof_path.is_absolute():
            prof_path = ROOT / prof_path
        audio_profile = load_audio_profile(prof_path if prof_path.is_file() else None)
        pro_audio_normalized = normalize_editor_stems(audio_out, audio_profile)
        snippet = output_dir / "_render_audio_profile.json"
        write_render_audio_snippet(audio_profile, snippet)
        pro_audio_profile_path = snippet

    pro_video_profile_path: Path | None = None
    if args.pro_video:
        vp = args.pro_video_profile
        if vp is None:
            vresolved = DEFAULT_VIDEO_PROFILE
        elif not vp.is_absolute():
            vresolved = ROOT / vp
        else:
            vresolved = vp
        video_profile = load_video_profile(vresolved if vresolved.is_file() else None)
        v_snippet = output_dir / "_render_video_profile.json"
        write_render_video_snippet(video_profile, v_snippet)
        pro_video_profile_path = v_snippet

    end_logo = args.end_logo_path or args.logo_path
    use_end_card = float(args.end_card_sec) > 0.0 and end_logo is not None
    render_output_name = "_body_pre_endcard.mp4" if use_end_card else args.output_name

    render_cmd_list = [
        sys.executable,
        str(ROOT / "scripts" / "render_s2_preset_v2.py"),
        "--input-dir",
        str(s2_dir),
        "--ducking",
        "--output-name",
        render_output_name,
        "--width",
        str(args.render_width),
        "--height",
        str(args.render_height),
        "--sfx-gain-db",
        str(args.sfx_gain_db),
        "--sfx-mix-weight",
        str(args.sfx_mix_weight),
    ]
    if pro_audio_profile_path is not None:
        render_cmd_list += ["--audio-profile-json", str(pro_audio_profile_path)]
    if pro_video_profile_path is not None:
        render_cmd_list += ["--video-profile-json", str(pro_video_profile_path)]
    render = run(render_cmd_list)

    body_mp4 = output_dir / render_output_name
    if use_end_card:
        end_src = end_logo if end_logo.is_absolute() else (ROOT / end_logo)
        if not end_src.is_file():
            raise RuntimeError(f"End card logo not found: {end_src}")
        tmp_end = output_dir / "_tmp_end_concat"
        tmp_end.mkdir(parents=True, exist_ok=True)
        append_end_logo_card(
            main_mp4=body_mp4,
            logo_png=end_src,
            out_mp4=final_target,
            width=int(args.render_width),
            height=int(args.render_height),
            duration_sec=float(args.end_card_sec),
            tmp_dir=tmp_end,
        )
        if body_mp4.is_file() and body_mp4 != final_target:
            body_mp4.unlink(missing_ok=True)
        final_mp4 = final_target
    else:
        final_mp4 = body_mp4
    gate = run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_movie_render_gate_v1.py"),
            "--video",
            str(final_mp4),
            "--script-text",
            str(args.scenario_file),
        ]
    )

    status = "PASS" if (render.returncode == 0 and gate.returncode == 0 and final_mp4.exists()) else "FAIL"
    report = {
        "schema": "athena_editor_v1_report",
        "generated_at_utc": now_utc(),
        "status": status,
        "inputs": {
            "input_clips_dir": str(clip_dir),
            "scenario_file": str(args.scenario_file),
            "shot_sec": args.shot_sec,
            "clip_count": len(source_clips),
            "s2_input_dir": str(s2_dir),
            "no_subtitles": args.no_subtitles,
            "no_narration": args.no_narration,
            "bgm_style": args.bgm_style,
            "bgm_file": str(args.bgm_file) if args.bgm_file else None,
            "logo_path": str(args.logo_path) if args.logo_path else None,
            "transition_sfx": args.transition_sfx,
            "promo_pack": args.promo_pack,
            "end_card_sec": args.end_card_sec,
            "end_logo_path": str(args.end_logo_path) if args.end_logo_path else None,
            "pro_audio": args.pro_audio,
            "pro_audio_profile": str(args.pro_audio_profile) if args.pro_audio_profile else None,
            "pro_audio_render_snippet": str(pro_audio_profile_path) if pro_audio_profile_path else None,
            "pro_audio_normalized_stems": pro_audio_normalized,
            "pro_video": args.pro_video,
            "pro_video_profile": str(args.pro_video_profile) if args.pro_video_profile else None,
            "pro_video_render_snippet": str(pro_video_profile_path) if pro_video_profile_path else None,
        },
        "outputs": {
            "final_mp4": str(final_mp4),
            "subtitle_srt": str(srt_path),
            "narration_wav": str(narr_wav),
            "bgm_wav": str(bgm_wav),
        },
        "steps": {
            "clip_normalization": norm_results,
            "render_returncode": render.returncode,
            "gate_returncode": gate.returncode,
        },
        "logs": {
            "render_stderr_tail": render.stderr[-1200:],
            "gate_stdout_tail": gate.stdout[-1200:],
        },
    }

    report_path = args.report_json if args.report_json.is_absolute() else (ROOT / args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": status == "PASS",
                "status": status,
                "final_mp4": str(final_mp4),
                "report_json": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

