#!/usr/bin/env python3
"""Probe edge-tts + ffmpeg for O-P31c Zone B render."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Check edge-tts/ffmpeg readiness for radio render.")
    ap.add_argument("--require-all", action="store_true")
    args = ap.parse_args()

    has_edge = False
    try:
        import edge_tts  # noqa: F401

        has_edge = True
    except ImportError:
        pass

    ffmpeg = shutil.which("ffmpeg")
    has_ffmpeg = bool(ffmpeg)
    ffmpeg_version = ""
    if has_ffmpeg:
        proc = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True)
        ffmpeg_version = (proc.stdout or "").splitlines()[0] if proc.returncode == 0 else ""

    ok = has_edge and has_ffmpeg
    out = {
        "edge_tts": has_edge,
        "ffmpeg": has_ffmpeg,
        "ffmpeg_path": ffmpeg or "",
        "ffmpeg_version_line": ffmpeg_version,
        "render_ready": ok,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.require_all and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
