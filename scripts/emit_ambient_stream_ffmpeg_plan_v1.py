#!/usr/bin/env python3
"""Emit FFmpeg RTMP plan from ambient_stream_manifest_v1 (dry-run; no stream key)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports" / "ambient_stream_manifest_latest.json"
DEFAULT_OUT = ROOT / "reports" / "ambient_stream_ffmpeg_plan_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_plan(manifest: Dict[str, Any], *, rtmp_url: str = "") -> Dict[str, Any]:
    playlist = manifest.get("playlist") or []
    tracks = [str(t.get("path") or "") for t in playlist if t.get("path")]
    visual = (manifest.get("visual_config") or {}).get("primary") or "static_frame"
    disclaimer = (manifest.get("caption_config") or {}).get("disclaimer_text_ko") or ""
    return {
        "schema": "ambient_stream_ffmpeg_plan_v1",
        "manifest_id": manifest.get("manifest_id"),
        "deployment_target": manifest.get("deployment_target"),
        "rtmp_url_set": bool(rtmp_url.strip()),
        "rtmp_url_redacted": "rtmp://***" if rtmp_url else "(set YOUTUBE_RTMP_URL env)",
        "playlist_paths": tracks,
        "visual_primary": visual,
        "disclaimer_interval_min": (manifest.get("caption_config") or {}).get("disclaimer_interval_min"),
        "suggested_commands": [
            "# 1) Loop BGM locally (example — replace paths)",
            "ffmpeg -stream_loop -1 -i <bed.mp3> -c:a aac -b:a 128k -f flv <RTMP_URL>",
            "# 2) Static image + audio (oracle_sphere_idle fallback)",
            "ffmpeg -loop 1 -i <frame.png> -stream_loop -1 -i <bed.mp3> "
            "-c:v libx264 -tune stillimage -pix_fmt yuv420p -c:a aac -shortest -f flv <RTMP_URL>",
        ],
        "disclaimer_overlay_note": disclaimer[:80] + ("…" if len(disclaimer) > 80 else ""),
        "safe_ops_note": "CF API 403 does not auto-stop this plan; use MKM_RADIO_STREAM_PAUSE=1 on host.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="FFmpeg plan for Zone A 24h ambient stream.")
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--rtmp-url", type=str, default="")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    path = args.manifest_json if args.manifest_json.is_absolute() else ROOT / args.manifest_json
    manifest = _read_json(path)
    rtmp = (args.rtmp_url or os.environ.get("YOUTUBE_RTMP_URL") or "").strip()
    plan = build_plan(manifest, rtmp_url=rtmp)
    payload = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
