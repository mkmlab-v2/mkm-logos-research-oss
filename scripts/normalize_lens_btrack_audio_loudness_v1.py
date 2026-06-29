#!/usr/bin/env python3
"""Apply ffmpeg loudnorm to lens B-track baked WAV loops (showroom delivery)."""

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
DEFAULT_HOOK = ROOT / "reports/track_c_audio_hook_samples_v1"
AUDIO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None


def _loudnorm(in_wav: Path, out_wav: Path, *, i_lufs: float, tp: float, lra: float) -> int:
    filt = f"loudnorm=I={i_lufs}:TP={tp}:LRA={lra}"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(in_wav),
        "-af",
        filt,
        "-ar",
        "32000",
        str(out_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hook-dir", type=Path, default=DEFAULT_HOOK)
    ap.add_argument("--lut", type=Path, default=AUDIO_LUT)
    ap.add_argument("--i-lufs", type=float, default=-16.0)
    ap.add_argument("--tp", type=float, default=-1.5)
    ap.add_argument("--lra", type=float, default=11.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not _ffmpeg_ok():
        print("[lens-audio-loudnorm] ffmpeg not found", file=sys.stderr)
        return 2
    if not args.lut.is_file():
        print(f"[lens-audio-loudnorm] missing LUT {args.lut}", file=sys.stderr)
        return 2

    lut = json.loads(args.lut.read_text(encoding="utf-8"))
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    clips: list[dict[str, Any]] = []
    ok = 0
    for pid, row in entries.items():
        if not isinstance(row, dict):
            continue
        fname = str(row.get("file") or "")
        if not fname.lower().endswith(".wav"):
            continue
        src = args.hook_dir / fname
        clip: dict[str, Any] = {"playback_id": pid, "file": fname, "status": "skip_missing"}
        if not src.is_file():
            clips.append(clip)
            continue
        if args.dry_run:
            clip["status"] = "dry_run"
            clips.append(clip)
            continue
        tmp = src.with_suffix(".loudnorm.tmp.wav")
        rc = _loudnorm(src, tmp, i_lufs=args.i_lufs, tp=args.tp, lra=args.lra)
        if rc == 0 and tmp.is_file() and tmp.stat().st_size > 0:
            tmp.replace(src)
            clip["status"] = "ok"
            ok += 1
        else:
            clip["status"] = "fail"
            clip["ffmpeg_exit"] = rc
            if tmp.is_file():
                tmp.unlink(missing_ok=True)
        clips.append(clip)

    lut["loudnorm_at_utc"] = _utc_now_z()
    lut["loudnorm_profile"] = {"I": args.i_lufs, "TP": args.tp, "LRA": args.lra}
    if not args.dry_run:
        args.lut.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "lens_btrack_audio_loudnorm_report_v1",
        "generated_at_utc": _utc_now_z(),
        "ok_count": ok,
        "total": len(clips),
        "clips": clips,
    }
    out = args.hook_dir / "lens_btrack_audio_loudnorm_report_v1_latest.json"
    if not args.dry_run:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-audio-loudnorm] ok={ok}/{len(clips)}")
    failed = [c for c in clips if c.get("status") == "fail"]
    missing = [c for c in clips if c.get("status") == "skip_missing"]
    if failed:
        return 1
    if missing and ok == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
