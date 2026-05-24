#!/usr/bin/env python3
"""O-P31c Zone A — ambient 24h stream manifest (playlist + disclaimer cadence)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PLAYLIST = ROOT / "data" / "radio" / "ambient_playlist_v1.example.json"
DEFAULT_OUT = ROOT / "reports" / "ambient_stream_manifest_latest.json"

from scripts.mkm_radio_dialogue_guard_v1 import DISCLAIMER_TEXT_KO  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_manifest(
    root: Path,
    *,
    playlist_path: Path = DEFAULT_PLAYLIST,
    bed_wav: Path | None = None,
) -> Dict[str, Any]:
    pl_doc = _read_json(playlist_path if playlist_path.is_absolute() else root / playlist_path)
    tracks: List[Dict[str, Any]] = list(pl_doc.get("tracks") or [])
    bed_path = bed_wav if bed_wav and bed_wav.is_absolute() else (root / bed_wav if bed_wav else None)
    if bed_path and bed_path.is_file():
        tracks = [
            {
                "track_id": "mkm_ambient_bed_loop",
                "path": bed_path.relative_to(root).as_posix(),
                "license_tag": "SELF_GENERATED",
                "license_url": "scripts/build_radio_ambient_bed_v1.py",
                "duration_sec": float(pl_doc.get("target_loop_seconds") or 120.0),
            }
        ]
    elif not tracks:
        tracks = [
            {
                "track_id": "placeholder_bed",
                "path": "reports/audio/placeholder_bed_loop.wav",
                "license_tag": "SELF_GENERATED",
                "license_url": "",
                "duration_sec": 120.0,
            }
        ]

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return {
        "schema": "ambient_stream_manifest_v1",
        "version": "1.0.0",
        "manifest_id": f"MKM-AMBIENT-{day}-001",
        "generated_at_utc": _utc_now(),
        "program_style": "ambient_24h_zone_a",
        "deployment_target": "YOUTUBE_LIVE_RTMP",
        "non_gating": True,
        "gates": {
            "public_facing_version": "1.7",
            "spoken_price_allowed": False,
            "human_review_required": False,
            "stream_pause_on_safe_ops_degraded": False,
        },
        "audio_bed_config": {
            "bgm_source_type": pl_doc.get("bgm_source_type") or "MIXED",
            "license_chain_pointer": "policies/audio_copyright_field.json",
            "crossfade_duration_sec": float(pl_doc.get("crossfade_duration_sec") or 4),
            "loop_playlist": True,
        },
        "caption_config": {
            "burn_in_disclaimer": True,
            "disclaimer_interval_min": int(pl_doc.get("disclaimer_interval_min") or 30),
            "disclaimer_text_ko": DISCLAIMER_TEXT_KO,
            "disclaimer_burn_in_ko": (
                "투자·의료·법률 자문 아님  |  관측·참고용 (실전 판단은 청취자)"
            ),
        },
        "brand_overlay": {
            "title_ko": "MKM Oracle Sphere",
            "subtitle_ko": "관측·참고용 · LIVE",
            "public_facing_version": "1.7",
        },
        "visual_config": {
            "primary": "oracle_sphere_idle",
            "fallback": "static_frame",
            "video_bed_path": "reports/video/oracle_sphere_idle_loop_latest.mp4",
            "fifo_playlist_path": "reports/ambient_stream_playlist_fifo.txt",
        },
        "ffmpeg_hints": {
            "video_size": "1280x720",
            "video_fps": "30",
            "audio_codec": "aac",
            "note": "Replace playlist paths with licensed beds before public RTMP.",
        },
        "playlist": tracks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ambient 24h stream manifest (Zone A).")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--playlist-json", type=Path, default=DEFAULT_PLAYLIST)
    ap.add_argument(
        "--bed-wav",
        type=Path,
        default=ROOT / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav",
        help="If file exists, overrides playlist with this BED track.",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    bed = args.bed_wav if args.bed_wav.is_absolute() else args.root / args.bed_wav
    doc = build_manifest(args.root, playlist_path=args.playlist_json, bed_wav=bed if bed.is_file() else None)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0
    out = args.out_json if args.out_json.is_absolute() else args.root / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
