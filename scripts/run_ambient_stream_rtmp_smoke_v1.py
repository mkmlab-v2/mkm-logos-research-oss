#!/usr/bin/env python3
"""Zone A — short RTMP push smoke test (L3). Requires Studio stream Ready + YOUTUBE_RTMP_URL."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_MANIFEST = ROOT / "reports" / "ambient_stream_manifest_latest.json"
DEFAULT_VIDEO = ROOT / "reports" / "video" / "oracle_sphere_idle_loop_latest.mp4"
DEFAULT_BED = ROOT / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav"
DEFAULT_OUT = ROOT / "reports" / "ambient_stream_rtmp_smoke_latest.json"

from scripts.emit_ambient_stream_rtmp_command_v1 import build_command, build_vf_filter  # noqa: E402


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rtmp_from_env() -> str:
    rtmp = (os.environ.get("YOUTUBE_RTMP_URL") or "").strip()
    if rtmp:
        return rtmp
    try:
        import winreg  # type: ignore[import-untyped]

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            val, _ = winreg.QueryValueEx(key, "YOUTUBE_RTMP_URL")
            return str(val or "").strip()
    except OSError:
        return ""


def build_smoke_argv(
    manifest: Dict[str, Any],
    *,
    video_mp4: Path,
    bed_wav: Path,
    rtmp_url: str,
    seconds: float,
) -> List[str]:
    vf = build_vf_filter(manifest)
    sec = max(5.0, min(300.0, float(seconds)))
    return [
        "ffmpeg",
        "-y",
        "-re",
        "-stream_loop",
        "-1",
        "-i",
        str(video_mp4.resolve()),
        "-re",
        "-stream_loop",
        "-1",
        "-i",
        str(bed_wav.resolve()),
        "-vf",
        vf,
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        "44100",
        "-t",
        str(sec),
        "-f",
        "flv",
        rtmp_url.strip(),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Zone A RTMP smoke push (timed, L3).")
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--video-mp4", type=Path, default=DEFAULT_VIDEO)
    ap.add_argument("--bed-wav", type=Path, default=DEFAULT_BED)
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--rtmp-url", type=str, default="")
    ap.add_argument("--dry-run", action="store_true", help="Print argv only; no ffmpeg push.")
    ap.add_argument(
        "--wall-timeout-sec",
        type=float,
        default=0.0,
        help="Kill ffmpeg if wall-clock exceeds this (default: probe_seconds + 90, max 300).",
    )
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if os.environ.get("MKM_RADIO_STREAM_PAUSE", "").strip().lower() in ("1", "true", "yes", "on"):
        doc = {"schema": "ambient_stream_rtmp_smoke_v1", "ok": False, "skipped": True, "reason": "MKM_RADIO_STREAM_PAUSE"}
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0

    rtmp = (args.rtmp_url or _rtmp_from_env()).strip()
    if not rtmp:
        print("FAIL: YOUTUBE_RTMP_URL unset — run Set-YoutubeRtmpUrlUserEnv_v1.ps1 -FromDotEnv", file=sys.stderr)
        return 1

    manifest_path = args.manifest_json if args.manifest_json.is_absolute() else ROOT / args.manifest_json
    if not manifest_path.is_file():
        print(f"FAIL: missing manifest {manifest_path}", file=sys.stderr)
        return 2

    video = args.video_mp4 if args.video_mp4.is_absolute() else ROOT / args.video_mp4
    bed = args.bed_wav if args.bed_wav.is_absolute() else ROOT / args.bed_wav
    for label, p in (("video", video), ("bed", bed)):
        if not p.is_file():
            print(f"FAIL: missing {label} {p}", file=sys.stderr)
            return 3

    manifest = _read_json(manifest_path)
    argv = build_smoke_argv(
        manifest,
        video_mp4=video,
        bed_wav=bed,
        rtmp_url=rtmp,
        seconds=args.seconds,
    )
    cmd_preview = build_command(
        manifest,
        playlist_txt=ROOT / "reports" / "ambient_stream_playlist_fifo.txt",
        video_mp4=video,
        rtmp_url=rtmp,
        profile="ambient_24h",
        bed_wav=bed,
    )

    doc: Dict[str, Any] = {
        "schema": "ambient_stream_rtmp_smoke_v1",
        "ok": False,
        "dry_run": bool(args.dry_run),
        "probe_seconds": args.seconds,
        "rtmp_configured": True,
        "rtmp_redacted": "rtmp://***" if rtmp else "",
        "24h_command_preview_head": cmd_preview[:120] + ("…" if len(cmd_preview) > 120 else ""),
        "studio_hint": "YouTube Studio stream must be Ready before smoke push.",
        "returncode": None,
        "stderr_tail": "",
    }

    if args.dry_run:
        doc["ok"] = True
        doc["argv"] = argv
    else:
        wall = float(args.wall_timeout_sec or 0.0)
        if wall <= 0:
            wall = min(300.0, max(60.0, float(args.seconds) + 90.0))
        doc["wall_timeout_sec"] = wall
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            _stdout, stderr = proc.communicate(timeout=wall)
            doc["returncode"] = proc.returncode
            doc["stderr_tail"] = (stderr or "")[-600:]
            doc["ok"] = proc.returncode == 0
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        text=True,
                    )
            doc["returncode"] = -9
            doc["stderr_tail"] = ""
            doc["ok"] = False
            doc["timeout"] = True
            doc["note"] = (
                f"ffmpeg exceeded wall timeout ({wall}s); "
                "check YouTube Studio stream Ready and RTMP ingest."
            )

    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
    else:
        out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(str(out))
    return 0 if doc.get("ok") else (doc.get("returncode") or 4)


if __name__ == "__main__":
    raise SystemExit(main())
