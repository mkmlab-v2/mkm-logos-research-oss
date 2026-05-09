#!/usr/bin/env python3
"""Generate local TTS/BGM and render final cinematic mp4.

Pipeline:
1) Ensure animatic clips exist (or generate via athena_film_maker_v1)
2) Build narration.wav using ffmpeg flite TTS from scenario text
3) Build bgm.wav using ffmpeg sine source
4) Render final video with scripts/render_s2_preset_v2.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
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
DEFAULT_BASE_OUT = ART / "cinematic_output"
DEFAULT_S2_DIR = ART / "cinematic_s2_input"
DEFAULT_REPORT = ART / "cinematic_tts_mix_pipeline_latest.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), text=True, capture_output=True)


def must_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required tool missing in PATH: {name}")


def ensure_animatic(base_out: Path, target_shots: int, shot_sec: int, scenario_file: Path) -> dict:
    film = base_out / "athena_film_sample_10s_latest.mp4"
    clips = base_out / "clips"
    if film.exists() and clips.exists():
        return {"generated": False, "reason": "existing_outputs_reused"}

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "cinematic" / "athena_film_maker_v1.py"),
        "--scenario-file",
        str(scenario_file),
        "--out-dir",
        str(base_out),
        "--target-shots",
        str(target_shots),
        "--shot-sec",
        str(shot_sec),
    ]
    p = run(cmd)
    return {
        "generated": True,
        "returncode": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


def build_tts_wav(text: str, out_wav: Path) -> dict:
    # Avoid inline filter parsing issues for long/UTF-8 text by using textfile mode.
    tts_dir = out_wav.parent
    tts_dir.mkdir(parents=True, exist_ok=True)
    text_file = tts_dir / "_narration_input.txt"
    text_file.write_text(text.replace("\r\n", "\n").strip() + "\n", encoding="utf-8")
    text_file_posix = text_file.as_posix().replace(":", r"\:")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"flite=textfile='{text_file_posix}':voice=slt",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(out_wav),
    ]
    p = run(cmd)
    return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def build_bgm_wav(duration_sec: float, out_wav: Path) -> dict:
    # Low-volume ambient-style tone for demo.
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=120:sample_rate=48000:duration={duration_sec}",
        "-filter:a",
        "volume=-22dB",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(out_wav),
    ]
    p = run(cmd)
    return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def ffprobe_duration(path: Path) -> float:
    p = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    if p.returncode != 0:
        return 0.0
    try:
        return float(p.stdout.strip())
    except Exception:
        return 0.0


def copy_clips_to_s2_input(src_clips: Path, s2_dir: Path) -> None:
    dst_clips = s2_dir / "clips"
    if dst_clips.exists():
        shutil.rmtree(dst_clips)
    dst_clips.mkdir(parents=True, exist_ok=True)
    for clip in sorted(src_clips.glob("*.mp4")):
        shutil.copy2(clip, dst_clips / clip.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--base-out", type=Path, default=DEFAULT_BASE_OUT)
    ap.add_argument("--s2-input-dir", type=Path, default=DEFAULT_S2_DIR)
    ap.add_argument("--target-shots", type=int, default=10)
    ap.add_argument("--shot-sec", type=int, default=10)
    ap.add_argument("--letterbox", action="store_true")
    ap.add_argument("--burnin-subtitles", action="store_true")
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument(
        "--pro-audio",
        action="store_true",
        help="LUFS stems + pass duck/mix JSON to render_s2_preset_v2 (same as athena_editor_v1 --pro-audio).",
    )
    ap.add_argument(
        "--pro-audio-profile",
        type=Path,
        default=None,
        help=f"Optional profile JSON (default: {DEFAULT_PROFILE.name}).",
    )
    ap.add_argument("--pro-video", action="store_true", help="LUT/video snippet for render (see pro_video_engine).")
    ap.add_argument(
        "--pro-video-profile",
        type=Path,
        default=None,
        help=f"Video profile JSON (default: {DEFAULT_VIDEO_PROFILE.name}).",
    )
    args = ap.parse_args()

    must_tool("ffmpeg")
    must_tool("ffprobe")

    base_out = args.base_out if args.base_out.is_absolute() else (ROOT / args.base_out)
    s2_dir = args.s2_input_dir if args.s2_input_dir.is_absolute() else (ROOT / args.s2_input_dir)
    base_out.mkdir(parents=True, exist_ok=True)
    s2_dir.mkdir(parents=True, exist_ok=True)

    scenario = args.scenario_file.read_text(encoding="utf-8").strip()
    animatic = ensure_animatic(base_out, args.target_shots, args.shot_sec, args.scenario_file)

    clips_dir = base_out / "clips"
    if not clips_dir.exists():
        raise RuntimeError("Missing clips directory after animatic step.")

    copy_clips_to_s2_input(clips_dir, s2_dir)
    if args.burnin_subtitles:
        srt_src = base_out / "athena_film_sample_10s_latest.srt"
        if srt_src.exists():
            subs_dir = s2_dir / "subtitles"
            subs_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(srt_src, subs_dir / "main.srt")
    audio_dir = s2_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    narration_wav = audio_dir / "narration.wav"
    bgm_wav = audio_dir / "bgm.wav"
    tts = build_tts_wav(scenario, narration_wav)

    total_duration = args.target_shots * args.shot_sec
    bgm = build_bgm_wav(float(total_duration), bgm_wav)

    pro_snippet: Path | None = None
    pro_normalized: list[str] = []
    if args.pro_audio:
        prof_path = args.pro_audio_profile
        if prof_path is None:
            resolved = DEFAULT_PROFILE
        elif prof_path.is_absolute():
            resolved = prof_path
        else:
            resolved = ROOT / prof_path
        audio_profile = load_audio_profile(resolved if resolved.is_file() else None)
        pro_normalized = normalize_editor_stems(audio_dir, audio_profile)
        out_dir = s2_dir / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        pro_snippet = out_dir / "_render_audio_profile.json"
        write_render_audio_snippet(audio_profile, pro_snippet)

    pro_video_snippet: Path | None = None
    if args.pro_video:
        vp = args.pro_video_profile
        if vp is None:
            vr = DEFAULT_VIDEO_PROFILE
        elif vp.is_absolute():
            vr = vp
        else:
            vr = ROOT / vp
        vprof = load_video_profile(vr if vr.is_file() else None)
        out_dir_v = s2_dir / "output"
        out_dir_v.mkdir(parents=True, exist_ok=True)
        pro_video_snippet = out_dir_v / "_render_video_profile.json"
        write_render_video_snippet(vprof, pro_video_snippet)

    # Render final using existing S2 preset renderer.
    render_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "render_s2_preset_v2.py"),
        "--input-dir",
        str(s2_dir),
        "--ducking",
    ]
    if args.letterbox:
        render_cmd.append("--letterbox")
    if pro_snippet is not None:
        render_cmd += ["--audio-profile-json", str(pro_snippet)]
    if pro_video_snippet is not None:
        render_cmd += ["--video-profile-json", str(pro_video_snippet)]
    render = run(render_cmd)

    final_mp4 = s2_dir / "output" / "final_s2_preset_v2.mp4"
    final_duration = ffprobe_duration(final_mp4) if final_mp4.exists() else 0.0

    status = "PASS" if (tts["returncode"] == 0 and bgm["returncode"] == 0 and render.returncode == 0 and final_mp4.exists()) else "FAIL"

    payload = {
        "schema": "cinematic_tts_mix_pipeline_v1",
        "generated_at_utc": now_utc(),
        "status": status,
        "inputs": {
            "scenario_file": str(args.scenario_file),
            "target_shots": args.target_shots,
            "shot_sec": args.shot_sec,
            "letterbox": args.letterbox,
            "burnin_subtitles": args.burnin_subtitles,
            "pro_audio": args.pro_audio,
            "pro_audio_profile": str(args.pro_audio_profile) if args.pro_audio_profile else None,
            "pro_audio_normalized_stems": pro_normalized,
            "pro_video": args.pro_video,
            "pro_video_profile": str(args.pro_video_profile) if args.pro_video_profile else None,
            "base_out": str(base_out),
            "s2_input_dir": str(s2_dir),
        },
        "steps": {
            "animatic": animatic,
            "tts_narration": tts["returncode"] == 0,
            "bgm_generation": bgm["returncode"] == 0,
            "s2_render": render.returncode == 0,
        },
        "outputs": {
            "narration_wav": str(narration_wav),
            "bgm_wav": str(bgm_wav),
            "final_mp4": str(final_mp4),
            "final_duration_sec": final_duration,
        },
        "logs": {
            "tts_stderr": tts["stderr"][-2000:],
            "bgm_stderr": bgm["stderr"][-2000:],
            "render_stderr": render.stderr[-2000:],
        },
    }

    report_path = args.report_json if args.report_json.is_absolute() else (ROOT / args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": status == "PASS", "status": status, "report_json": str(report_path), "final_mp4": str(final_mp4)}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

