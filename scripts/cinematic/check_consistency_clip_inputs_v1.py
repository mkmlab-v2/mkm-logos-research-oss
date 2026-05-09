#!/usr/bin/env python3
"""Validate shot clip inputs for cinematic_consistency_pack_v1 workspace."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_ROOT = ART / "cinematic_consistency_pack_v1"
DEFAULT_REPORT = ART / "consistency_clip_input_check_latest.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def ffprobe_video(path: Path) -> dict:
    p = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    if p.returncode != 0:
        return {"ok": False, "error": p.stderr.strip()[-400:]}
    try:
        data = json.loads(p.stdout or "{}")
    except Exception as e:
        return {"ok": False, "error": f"json parse error: {e}"}
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    return {
        "ok": True,
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "r_frame_rate": stream.get("r_frame_rate") or "",
        "duration_sec": float(fmt.get("duration") or 0.0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root-dir", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--shot-count", type=int, default=10)
    ap.add_argument("--target-shot-sec", type=float, default=6.0)
    ap.add_argument("--duration-tolerance-sec", type=float, default=0.8)
    ap.add_argument("--min-width", type=int, default=1280)
    ap.add_argument("--min-height", type=int, default=720)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    root_dir = args.root_dir if args.root_dir.is_absolute() else (ROOT / args.root_dir)
    shots_dir = root_dir / "shots"
    if not shots_dir.exists():
        raise RuntimeError(f"shots directory not found: {shots_dir}")

    checks = []
    blocking_errors = []
    warnings = []

    for i in range(1, args.shot_count + 1):
        sid = f"shot_{i:02d}"
        sdir = shots_dir / sid
        clip = sdir / "clip.mp4"
        first_frame = sdir / "first_frame.png"
        last_frame = sdir / "last_frame.png"
        shot_result = {
            "shot_id": sid,
            "clip_path": str(clip),
            "exists": clip.exists(),
            "first_frame_exists": first_frame.exists(),
            "last_frame_exists": last_frame.exists(),
            "ok": False,
            "issues": [],
            "warnings": [],
            "probe": {},
        }

        if not clip.exists():
            shot_result["issues"].append("missing clip.mp4")
            blocking_errors.append(f"{sid}: missing clip.mp4")
            checks.append(shot_result)
            continue

        probe = ffprobe_video(clip)
        shot_result["probe"] = probe
        if not probe.get("ok"):
            msg = f"ffprobe failed: {probe.get('error','unknown')}"
            shot_result["issues"].append(msg)
            blocking_errors.append(f"{sid}: {msg}")
            checks.append(shot_result)
            continue

        w = int(probe["width"])
        h = int(probe["height"])
        dur = float(probe["duration_sec"])

        if w < args.min_width or h < args.min_height:
            msg = f"resolution too low ({w}x{h})"
            shot_result["issues"].append(msg)
            blocking_errors.append(f"{sid}: {msg}")

        if abs(dur - args.target_shot_sec) > args.duration_tolerance_sec:
            msg = f"duration out of range ({dur:.2f}s)"
            shot_result["issues"].append(msg)
            blocking_errors.append(f"{sid}: {msg}")

        # frame chain artifacts are warnings, not blockers
        if i > 1 and not first_frame.exists():
            shot_result["warnings"].append("first_frame.png missing (chain debug harder)")
            warnings.append(f"{sid}: first_frame.png missing")
        if not last_frame.exists():
            shot_result["warnings"].append("last_frame.png missing (next-shot reference unavailable)")
            warnings.append(f"{sid}: last_frame.png missing")

        shot_result["ok"] = len(shot_result["issues"]) == 0
        checks.append(shot_result)

    status = "PASS" if not blocking_errors else "FAIL"
    payload = {
        "schema": "consistency_clip_input_check_v1",
        "generated_at_utc": now_utc(),
        "status": status,
        "inputs": {
            "root_dir": str(root_dir),
            "shot_count": args.shot_count,
            "target_shot_sec": args.target_shot_sec,
            "duration_tolerance_sec": args.duration_tolerance_sec,
            "min_width": args.min_width,
            "min_height": args.min_height,
        },
        "summary": {
            "total_shots": args.shot_count,
            "blocking_error_count": len(blocking_errors),
            "warning_count": len(warnings),
        },
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "checks": checks,
    }

    report_path = args.report_json if args.report_json.is_absolute() else (ROOT / args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": status == "PASS",
                "status": status,
                "report_json": str(report_path),
                "blocking_errors": len(blocking_errors),
                "warnings": len(warnings),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

