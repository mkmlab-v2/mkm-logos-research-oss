#!/usr/bin/env python3
"""Emit 12-pair audio + video playback LUT latest/example artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_btrack_playback_matrix_v1 import (  # noqa: E402
    build_audio_lut,
    build_video_lut,
    matrix_pair_count,
)

AUDIO_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1.example.json"
AUDIO_LATEST = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"
VIDEO_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1.example.json"
VIDEO_LATEST = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Build 12-pair lens B-track playback LUTs")
    p.add_argument("--version", default=None, help="LUT version YYYY-MM-DD (default: UTC today)")
    args = p.parse_args()

    audio = build_audio_lut(version=args.version)
    video = build_video_lut(version=args.version)
    n = matrix_pair_count()
    if len(audio.get("entries", {})) != n or len(video.get("entries", {})) != n:
        print(f"[lens-lut-matrix] FAIL: expected {n} entries", file=sys.stderr)
        return 1

    for path in (AUDIO_EXAMPLE, AUDIO_LATEST, VIDEO_EXAMPLE, VIDEO_LATEST):
        _write(path, audio if "audio" in path.name else video)

    print(f"[lens-lut-matrix] WROTE audio: {AUDIO_LATEST} ({n} entries)")
    print(f"[lens-lut-matrix] WROTE video: {VIDEO_LATEST} ({n} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
