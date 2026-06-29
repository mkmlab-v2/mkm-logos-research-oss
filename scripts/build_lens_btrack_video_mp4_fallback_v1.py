#!/usr/bin/env python3
"""Transcode lens B-track WebM loops to H.264 MP4 for Safari / broader browser support."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOOK = ROOT / "reports/track_c_video_hook_samples_v1"
VIDEO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None


def _transcode(webm: Path, mp4: Path) -> int:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(webm),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hook-dir", type=Path, default=DEFAULT_HOOK)
    ap.add_argument("--lut", type=Path, default=VIDEO_LUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not _ffmpeg_ok():
        print("[lens-video-mp4] ffmpeg not found", file=sys.stderr)
        return 2
    if not args.lut.is_file():
        print(f"[lens-video-mp4] missing LUT {args.lut}", file=sys.stderr)
        return 2

    lut = json.loads(args.lut.read_text(encoding="utf-8"))
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    clips: list[dict[str, Any]] = []
    ok = 0
    for vid, row in entries.items():
        if not isinstance(row, dict):
            continue
        webm_name = str(row.get("file") or "")
        if not webm_name.lower().endswith(".webm"):
            continue
        mp4_name = webm_name[:-5] + ".mp4"
        webm = args.hook_dir / webm_name
        mp4 = args.hook_dir / mp4_name
        clip: dict[str, Any] = {
            "video_playback_id": vid,
            "webm": webm_name,
            "mp4": mp4_name,
            "status": "skip_missing_webm",
        }
        if not webm.is_file():
            clips.append(clip)
            continue
        if mp4.is_file() and mp4.stat().st_mtime >= webm.stat().st_mtime:
            row["mp4_file"] = mp4_name
            clip["status"] = "ok_cached"
            ok += 1
            clips.append(clip)
            continue
        if args.dry_run:
            clip["status"] = "dry_run"
            clips.append(clip)
            continue
        rc = _transcode(webm, mp4)
        if rc == 0 and mp4.is_file():
            row["mp4_file"] = mp4_name
            clip["status"] = "ok"
            ok += 1
        else:
            clip["status"] = "fail"
            clip["ffmpeg_exit"] = rc
        clips.append(clip)

    lut["mp4_fallback_at_utc"] = _utc_now_z()
    if not args.dry_run:
        args.lut.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ex = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1.example.json"
        if ex.is_file() or args.lut == VIDEO_LUT:
            ex.parent.mkdir(parents=True, exist_ok=True)
            ex.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "lens_btrack_video_mp4_fallback_report_v1",
        "generated_at_utc": _utc_now_z(),
        "ok_count": ok,
        "total": len(clips),
        "clips": clips,
    }
    out = args.hook_dir / "lens_btrack_video_mp4_fallback_report_v1_latest.json"
    if not args.dry_run:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-video-mp4] ok={ok}/{len(clips)} lut={args.lut}")
    return 0 if ok == len(clips) and clips else 1 if ok == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
