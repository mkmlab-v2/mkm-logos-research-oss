#!/usr/bin/env python3
"""Zone A — local quality audit before RTMP (no upload, no API cost)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MANIFEST = ROOT / "reports" / "ambient_stream_manifest_latest.json"
DEFAULT_VIDEO = ROOT / "reports" / "video" / "oracle_sphere_idle_loop_latest.mp4"
DEFAULT_BED = ROOT / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav"
DEFAULT_OUT = ROOT / "reports" / "ambient_stream_quality_audit_latest.json"
DEFAULT_PREVIEW = ROOT / "reports" / "video" / "zone_a_local_preview_latest.mp4"

from scripts.emit_ambient_stream_rtmp_command_v1 import (  # noqa: E402
    build_vf_filter,
    uses_premium_ui_overlay,
)
from scripts.zone_a_broadcast_visual_premium_v1 import (  # noqa: E402
    UI_OVERLAY,
    build_preview_mp4,
)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _ffprobe_streams(path: Path) -> Tuple[Dict[str, Any], str]:
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_name,width,height,r_frame_rate,sample_rate,channels,duration,bit_rate",
        "-of",
        "json",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}, (proc.stderr or "")[-400:]
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {}, "ffprobe_json_parse_error"
    streams = data.get("streams") or []
    return (streams[0] if streams else {}), ""


def _frame_mean_luma(video: Path, *, at_sec: float = 5.0) -> Dict[str, Any]:
    """Sample center-frame luma; reject near-black beds (failed sphere render)."""
    jpg = video.parent / "_audit_luma_sample.jpg"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-v",
        "error",
        "-ss",
        str(at_sec),
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(jpg),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not jpg.is_file():
        return {"ok": False, "mean_luma": 0.0, "reason": "frame_extract_failed"}
    try:
        from PIL import Image  # type: ignore[import-untyped]

        im = Image.open(jpg).convert("L")
        pixels = list(im.getdata())
        mean = sum(pixels) / max(1, len(pixels))
        ok = mean >= 28.0
        return {"ok": ok, "mean_luma": round(mean, 2), "threshold": 28.0}
    except ImportError:
        # Pillow optional — size heuristic only
        ok = jpg.stat().st_size > 8000
        return {"ok": ok, "mean_luma": None, "reason": "pillow_unavailable_size_proxy"}
    finally:
        if jpg.is_file():
            jpg.unlink(missing_ok=True)


def _decode_probe(path: Path, *, seconds: float = 10.0) -> Dict[str, Any]:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-v",
        "error",
        "-t",
        str(seconds),
        "-i",
        str(path),
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    err = proc.stderr or ""
    nal_hits = len(re.findall(r"Invalid NAL unit", err))
    decoder_hits = len(re.findall(r"Error submitting packet to decoder", err))
    return {
        "ok": proc.returncode == 0 and nal_hits == 0 and decoder_hits == 0,
        "returncode": proc.returncode,
        "nal_error_count": nal_hits,
        "decoder_error_count": decoder_hits,
        "stderr_tail": err[-500:],
    }


def _render_preview(
    manifest: Dict[str, Any],
    *,
    video: Path,
    bed: Path,
    out_mp4: Path,
    seconds: float,
) -> Dict[str, Any]:
    sec = max(5.0, min(60.0, float(seconds)))
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    ui = UI_OVERLAY if UI_OVERLAY.is_absolute() else ROOT / UI_OVERLAY
    if uses_premium_ui_overlay(ui):
        proc = build_preview_mp4(video, ui, bed, out_mp4, seconds=sec)
        mode = "premium_png_overlay"
    else:
        vf = build_vf_filter(manifest)
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-v",
            "error",
            "-t",
            str(sec),
            "-i",
            str(video.resolve()),
            "-i",
            str(bed.resolve()),
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
            "-shortest",
            str(out_mp4.resolve()),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        mode = "drawtext"
    return {
        "ok": proc.returncode == 0 and out_mp4.is_file() and out_mp4.stat().st_size > 10_000,
        "returncode": proc.returncode,
        "out_path": str(out_mp4.relative_to(ROOT)).replace("\\", "/"),
        "bytes": out_mp4.stat().st_size if out_mp4.is_file() else 0,
        "stderr_tail": (proc.stderr or "")[-500:],
        "overlay_mode": mode,
    }


def build_audit(
    root: Path,
    *,
    preview_seconds: float,
    write_preview: bool,
) -> Dict[str, Any]:
    manifest_path = root / "reports" / "ambient_stream_manifest_latest.json"
    video = root / "reports" / "video" / "oracle_sphere_idle_loop_latest.mp4"
    bed = root / "reports/audio/mkm_ambient_bed_loop_latest.wav"
    issues: List[str] = []
    warnings: List[str] = []

    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    rows: Dict[str, Any] = {
        "video_exists": video.is_file(),
        "bed_exists": bed.is_file(),
        "manifest_exists": manifest_path.is_file(),
    }
    if not rows["video_exists"]:
        issues.append("missing_oracle_sphere_mp4")
    if not rows["bed_exists"]:
        issues.append("missing_ambient_bed_wav")

    video_stream: Dict[str, Any] = {}
    bed_stream: Dict[str, Any] = {}
    if video.is_file():
        video_stream, v_err = _ffprobe_streams(video)
        if v_err:
            warnings.append("video_ffprobe_stderr")
        w = int(video_stream.get("width") or 0)
        h = int(video_stream.get("height") or 0)
        if w < 1280 or h < 720:
            warnings.append(f"video_resolution_low_{w}x{h}")
        if w >= 1920 and h >= 1080:
            rows["video_tier"] = "1080p_ok"
        elif w >= 1280:
            rows["video_tier"] = "720p_acceptable"
        rows["video_decode"] = _decode_probe(video, seconds=10.0)
        if not rows["video_decode"].get("ok"):
            issues.append("video_decode_errors_reencode_required")
        rows["video_luma"] = _frame_mean_luma(video, at_sec=min(5.0, float(video_stream.get("duration") or 10) / 2))
        if rows["video_luma"].get("ok") is False:
            issues.append("video_too_dark_reencode_broadcast_profile")

    if bed.is_file():
        bed_stream, _ = _ffprobe_streams(bed)
        rows["bed_decode"] = _decode_probe(bed, seconds=5.0)
        if not rows["bed_decode"].get("ok"):
            issues.append("bed_decode_failed")

    preview: Dict[str, Any] = {"skipped": True}
    if write_preview and video.is_file() and bed.is_file() and manifest:
        preview = _render_preview(
            manifest,
            video=video,
            bed=bed,
            out_mp4=root / "reports" / "video" / "zone_a_local_preview_latest.mp4",
            seconds=preview_seconds,
        )
        if not preview.get("ok"):
            issues.append("local_preview_render_failed")

    broadcast_ready = not issues
    return {
        "schema": "ambient_stream_quality_audit_v1",
        "broadcast_ready": broadcast_ready,
        "quality_gate": "pass" if broadcast_ready else "hold",
        "issues": issues,
        "warnings": warnings,
        "cost_note": (
            "Local audit + preview: $0 cloud API. RTMP smoke/24h: no YouTube ingest fee; "
            "ISP upload + PC power only."
        ),
        "recommended_order": [
            "1) py scripts/run_ambient_stream_quality_audit_v1.py --write-preview",
            "2) Open reports/video/zone_a_local_preview_latest.mp4 (eyes/ears)",
            "3) If pass: Studio Ready → py scripts/run_ambient_stream_rtmp_smoke_v1.py --seconds 30",
            "4) If pass: Invoke-ZoneALiveBroadcastPrep -GoLive",
        ],
        "files": rows,
        "video_stream": video_stream,
        "bed_stream": bed_stream,
        "local_preview": preview,
        "disclaimer_present": bool((manifest.get("caption_config") or {}).get("disclaimer_text_ko")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Zone A quality audit (local, no RTMP).")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--preview-seconds", type=float, default=20.0)
    ap.add_argument("--write-preview", action="store_true", help="Render local MP4 with burn-in overlays.")
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_audit(args.root, preview_seconds=args.preview_seconds, write_preview=args.write_preview)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
    else:
        out = args.out_json if args.out_json.is_absolute() else args.root / args.out_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(str(out))
    return 0 if doc.get("broadcast_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
