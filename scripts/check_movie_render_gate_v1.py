#!/usr/bin/env python3
"""Quality gate for rendered movie outputs (black frame, loudness/peak, keyword presence)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "docs" / "final" / "artifacts" / "athena_movie_engine_profile_google_cost_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "athena_movie_engine_gate_latest.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)


def ffprobe_duration(video: Path) -> float:
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ]
    ).strip()
    return float(out)


def black_ratio(video: Path) -> float:
    out = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(video),
            "-vf",
            "blackdetect=d=0.10:pix_th=0.10",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    total_black = 0.0
    for line in out.splitlines():
        if "black_duration:" in line:
            try:
                val = line.split("black_duration:")[1].strip()
                total_black += float(val)
            except Exception:
                pass
    dur = max(0.001, ffprobe_duration(video))
    return total_black / dur


def peak_dbfs(video: Path) -> float:
    out = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(video),
            "-af",
            "astats=metadata=1:reset=1",
            "-f",
            "null",
            "-",
        ]
    )
    best = -99.0
    for line in out.splitlines():
        if "Peak level dB" in line:
            try:
                value = float(line.split(":")[-1].strip())
                best = max(best, value)
            except Exception:
                pass
    return best


def keywords_pass(script_text: str, required: list[str]) -> dict[str, bool]:
    return {k: (k in script_text) for k in required}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--script-text", type=Path, required=False)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    profile: dict[str, Any] = json.loads(args.profile_json.read_text(encoding="utf-8"))
    gate = profile.get("quality_gate", {})
    max_black = float(gate.get("max_black_frame_ratio", 0.0))
    max_peak = float(gate.get("max_true_peak_dbfs", -1.0))
    required = list(gate.get("required_keywords", []))

    br = black_ratio(args.video)
    peak = peak_dbfs(args.video)

    script_text = ""
    if args.script_text and args.script_text.is_file():
        script_text = args.script_text.read_text(encoding="utf-8")
    kw = keywords_pass(script_text, required) if required else {}

    checks = {
        "black_frame_ratio_ok": br <= max_black,
        "peak_dbfs_ok": peak <= max_peak,
        "required_keywords_ok": all(kw.values()) if kw else True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"

    doc = {
        "schema": "athena_movie_engine_gate_v1",
        "generated_at_utc": now_utc(),
        "inputs": {
            "video": str(args.video),
            "script_text": str(args.script_text) if args.script_text else None,
            "profile_json": str(args.profile_json),
        },
        "metrics": {
            "black_frame_ratio": br,
            "peak_dbfs": peak,
            "keyword_presence": kw,
        },
        "checks": checks,
        "status": status,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(args.output_json)}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
