#!/usr/bin/env python3
"""Create 10-shot x 6s consistency workspace and ffmpeg template."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_ROOT = ART / "cinematic_consistency_pack_v1"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root-dir", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--shot-count", type=int, default=10)
    ap.add_argument("--shot-sec", type=int, default=6)
    args = ap.parse_args()

    root_dir = args.root_dir if args.root_dir.is_absolute() else (ROOT / args.root_dir)
    refs = root_dir / "references"
    shots = root_dir / "shots"
    deliver = root_dir / "deliverables"

    refs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    deliver.mkdir(parents=True, exist_ok=True)

    (refs / "master_character.png").touch(exist_ok=True)
    (refs / "master_location.png").touch(exist_ok=True)
    (refs / "hero_grade_reference.png").touch(exist_ok=True)

    for i in range(1, args.shot_count + 1):
        sdir = shots / f"shot_{i:02d}"
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "prompt.txt").write_text(
            f"SHOT {i:02d} prompt placeholder. duration={args.shot_sec}s\n",
            encoding="utf-8",
        )
        (sdir / "negative_prompt.txt").write_text(
            "identity drift, warped face, style jump, watermark, bad anatomy\n",
            encoding="utf-8",
        )
        (sdir / "notes.txt").write_text(
            "Put generated clip as clip.mp4. Export first_frame.png and last_frame.png.\n",
            encoding="utf-8",
        )

    (root_dir / "ffmpeg_assemble_template.ps1").write_text(
        (
            "$Root = Split-Path -Parent $MyInvocation.MyCommand.Path\n"
            "$S2 = Join-Path $Root \"s2_input\"\n"
            "$Clips = Join-Path $S2 \"clips\"\n"
            "$Audio = Join-Path $S2 \"audio\"\n"
            "$Subs = Join-Path $S2 \"subtitles\"\n"
            "New-Item -ItemType Directory -Path $Clips,$Audio,$Subs -Force | Out-Null\n"
            "Get-ChildItem (Join-Path $Root \"shots\") -Directory | Sort-Object Name | ForEach-Object {\n"
            "  $c = Join-Path $_.FullName \"clip.mp4\"\n"
            "  if (Test-Path $c) { Copy-Item $c (Join-Path $Clips ($_.Name + \".mp4\")) -Force }\n"
            "}\n"
            "Write-Host \"Now place narration.wav, bgm.wav, main.srt under s2_input/audio|subtitles and run:\"\n"
            "Write-Host \"py scripts/render_s2_preset_v2.py --input-dir $S2 --ducking --output-name final_consistency_pack_v1.mp4\"\n"
            "Write-Host \"Optional pro mix: --audio-profile-json docs/final/artifacts/athena_pro_audio_profile_v1.json\"\n"
            "Write-Host \"Optional LUT: --video-profile-json docs/final/artifacts/athena_pro_video_profile_v1.json\"\n"
        ),
        encoding="utf-8",
    )

    (root_dir / "README.txt").write_text(
        (
            "MKM Consistency Pack v1\n"
            "1) Fill references/master_character.png and master_location.png\n"
            "2) Generate clips in shots/shot_XX/clip.mp4 with chained last_frame references\n"
            "3) Use ffmpeg_assemble_template.ps1 to gather clips\n"
            "4) Render final output via scripts/render_s2_preset_v2.py\n"
        ),
        encoding="utf-8",
    )

    print(f"ok: {root_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

