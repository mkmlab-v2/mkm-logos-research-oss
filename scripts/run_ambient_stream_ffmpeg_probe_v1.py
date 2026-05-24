#!/usr/bin/env python3
"""Probe Zone A BED decode via ffmpeg (no RTMP). Validates manifest playlist paths."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports" / "ambient_stream_manifest_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="FFmpeg probe ambient BED (null muxer).")
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--probe-seconds", type=float, default=5.0)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    path = args.manifest_json if args.manifest_json.is_absolute() else ROOT / args.manifest_json
    manifest = _read_json(path)
    playlist = manifest.get("playlist") or []
    if not playlist:
        print("FAIL: empty playlist", file=sys.stderr)
        return 1

    bed_rel = str(playlist[0].get("path") or "")
    bed = ROOT / bed_rel
    if not bed.is_file():
        print(f"FAIL: missing bed {bed}", file=sys.stderr)
        return 2

    if os.environ.get("MKM_RADIO_STREAM_PAUSE", "").strip().lower() in ("1", "true", "yes", "on"):
        print(json.dumps({"ok": False, "skipped": True, "reason": "MKM_RADIO_STREAM_PAUSE"}))
        return 0

    sec = max(1.0, min(30.0, float(args.probe_seconds)))
    cmd = [
        "ffmpeg",
        "-y",
        "-t",
        str(sec),
        "-stream_loop",
        "0",
        "-i",
        str(bed),
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    doc = {
        "schema": "ambient_stream_ffmpeg_probe_v1",
        "ok": proc.returncode == 0,
        "bed_path": bed_rel,
        "probe_seconds": sec,
        "returncode": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-400:],
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
    else:
        out = ROOT / "reports" / "ambient_stream_ffmpeg_probe_latest.json"
        out.write_text(payload + "\n", encoding="utf-8")
        print(str(out))
    return 0 if doc["ok"] else proc.returncode or 3


if __name__ == "__main__":
    raise SystemExit(main())
