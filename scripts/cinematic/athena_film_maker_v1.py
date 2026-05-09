#!/usr/bin/env python3
"""Local cinematic pipeline (scenario -> shot clips -> merged short film).

MVP mode is animatic-first:
- Build deterministic 16:9 shot clips with ffmpeg (color + overlay text)
- Concatenate clips into a single mp4
- Emit SRT and run report for quick iteration

This is intended for immediate local execution and later extension
to model-based generation backends.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCENARIO = ART / "cinematic_scenario_sample_v1.txt"
DEFAULT_OUT_DIR = ART / "cinematic_output"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg/ffprobe not found in PATH.")


def ensure_default_scenario(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "도시의 새벽, 고요한 거리 위로 첫 빛이 번진다.",
                "작은 실험실에서 엔지니어가 시스템 로그를 확인한다.",
                "화면 위 수치가 안정적으로 수렴하는 장면을 클로즈업한다.",
                "위험 입력이 들어오자 WATCH/HOLD 게이트가 작동한다.",
                "오류 없이 안전 경로로 전환되는 흐름을 보여준다.",
                "팀이 결과를 검토하고 다음 단계 계획을 확정한다.",
                "마지막으로 신뢰와 검증을 상징하는 문구로 마무리한다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def split_scenario_lines(text: str, target_shots: int) -> list[str]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        return ["장면 설명이 비어 있어 기본 타이틀 카드로 대체됩니다."]
    if len(lines) >= target_shots:
        return lines[:target_shots]
    out = list(lines)
    while len(out) < target_shots:
        out.append(lines[len(out) % len(lines)])
    return out


def sec_to_srt(ts: float) -> str:
    h = int(ts // 3600)
    m = int((ts % 3600) // 60)
    s = int(ts % 60)
    ms = int((ts - math.floor(ts)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(shots: list[str], shot_sec: int, path: Path) -> None:
    cur = 0.0
    blocks: list[str] = []
    for i, line in enumerate(shots, start=1):
        start = sec_to_srt(cur)
        end = sec_to_srt(cur + float(shot_sec))
        blocks.append(f"{i}\n{start} --> {end}\n{line}\n")
        cur += float(shot_sec)
    path.write_text("\n".join(blocks), encoding="utf-8")


def make_shot_clip(
    *,
    text: str,
    idx: int,
    shot_sec: int,
    width: int,
    height: int,
    fps: int,
    out_path: Path,
) -> None:
    safe_text = text.replace(":", r"\:").replace("'", r"\'")
    palette = ["#1f2937", "#1e3a8a", "#0f766e", "#7c2d12", "#3f3f46", "#334155"]
    bg_color = palette[(idx - 1) % len(palette)]
    # drawtext uses default system font fallback; this keeps setup dependency-free.
    vf = (
        f"drawbox=x=0:y=0:w=iw:h=126:color=black@0.52:t=fill,"
        f"drawbox=x=mod(t*220\\,(iw-220)):y=h*0.18:w=220:h=96:color=white@0.16:t=fill,"
        f"drawbox=x=mod(t*140+300\\,(iw-180)):y=h*0.64:w=180:h=72:color=black@0.20:t=fill,"
        f"drawtext=text='SHOT {idx:02d}':x=44:y=34:fontsize=48:fontcolor=white:borderw=2:bordercolor=black@0.7,"
        f"drawtext=text='{safe_text}':x=40:y=h-120:fontsize=42:fontcolor=white:borderw=3:bordercolor=black@0.75"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={bg_color}:s={width}x{height}:d={shot_sec}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={440 + idx * 25}:sample_rate=48000:duration={shot_sec}",
        "-vf",
        vf,
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(out_path),
    ]
    run(cmd)


def concat_clips(clips: list[Path], out_path: Path) -> None:
    list_path = out_path.parent / "_concat_list.txt"
    list_path.write_text("\n".join([f"file '{c.as_posix()}'" for c in clips]) + "\n", encoding="utf-8")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(out_path),
    ]
    run(cmd)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--target-shots", type=int, default=10)
    ap.add_argument("--shot-sec", type=int, default=10)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_ffmpeg()
    ensure_default_scenario(args.scenario_file)

    out_dir = args.out_dir if args.out_dir.is_absolute() else (ROOT / args.out_dir)
    clips_dir = out_dir / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    scenario_text = args.scenario_file.read_text(encoding="utf-8")
    shots = split_scenario_lines(scenario_text, args.target_shots)

    clip_paths: list[Path] = []
    for i, shot in enumerate(shots, start=1):
        clip = clips_dir / f"shot_{i:02d}.mp4"
        clip_paths.append(clip)
        if not args.dry_run:
            make_shot_clip(
                text=shot,
                idx=i,
                shot_sec=args.shot_sec,
                width=args.width,
                height=args.height,
                fps=args.fps,
                out_path=clip,
            )

    film_path = out_dir / "athena_film_sample_10s_latest.mp4"
    srt_path = out_dir / "athena_film_sample_10s_latest.srt"
    report_path = out_dir / "athena_film_sample_10s_report_latest.json"

    if not args.dry_run:
        concat_clips(clip_paths, film_path)
        build_srt(shots, args.shot_sec, srt_path)

    report: dict[str, Any] = {
        "schema": "athena_film_maker_v1_report",
        "generated_at_utc": now_utc(),
        "scenario_file": str(args.scenario_file),
        "settings": {
            "target_shots": args.target_shots,
            "shot_sec": args.shot_sec,
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "mode": "animatic_local_ffmpeg",
            "dry_run": args.dry_run,
        },
        "outputs": {
            "film_mp4": str(film_path),
            "subtitle_srt": str(srt_path),
            "clips_dir": str(clips_dir),
        },
        "summary": {
            "shot_count": len(shots),
            "total_duration_sec": len(shots) * args.shot_sec,
            "ready_for_next_step": not args.dry_run,
        },
        "next_steps": [
            "Replace animatic clips with model-generated clips (SVD/CogVideoX) while preserving shot timing.",
            "Replace sine tone with TTS narration and BGM track.",
            "Run quality gate script on final mp4.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "film_mp4": str(film_path),
                "subtitle_srt": str(srt_path),
                "report_json": str(report_path),
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

