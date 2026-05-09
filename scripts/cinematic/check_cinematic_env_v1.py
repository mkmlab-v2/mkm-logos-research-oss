#!/usr/bin/env python3
"""Check local environment for cinematic pipeline."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "final" / "artifacts" / "cinematic_env_check_latest.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, text=True, capture_output=True)
    text = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    merged = text if text else err
    return p.returncode, merged


def which(name: str) -> str | None:
    return shutil.which(name)


def main() -> int:
    py_version = sys.version.split()[0]
    ffmpeg_path = which("ffmpeg")
    ffprobe_path = which("ffprobe")
    nvidia_smi_path = which("nvidia-smi")

    ffmpeg_ok = False
    ffprobe_ok = False
    gpu_ok = False

    ffmpeg_ver = ""
    ffprobe_ver = ""
    gpu_text = ""

    if ffmpeg_path:
        code, out = run(["ffmpeg", "-version"])
        ffmpeg_ok = code == 0
        ffmpeg_ver = out.splitlines()[0] if out else ""

    if ffprobe_path:
        code, out = run(["ffprobe", "-version"])
        ffprobe_ok = code == 0
        ffprobe_ver = out.splitlines()[0] if out else ""

    if nvidia_smi_path:
        code, out = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
        gpu_ok = code == 0
        gpu_text = out

    status = "READY" if ffmpeg_ok and ffprobe_ok else "NOT_READY"

    payload = {
        "schema": "cinematic_env_check_v1",
        "generated_at_utc": now_utc(),
        "status": status,
        "python_version": py_version,
        "checks": {
            "ffmpeg_ok": ffmpeg_ok,
            "ffprobe_ok": ffprobe_ok,
            "nvidia_smi_present": bool(nvidia_smi_path),
            "gpu_query_ok": gpu_ok,
        },
        "details": {
            "ffmpeg_path": ffmpeg_path,
            "ffprobe_path": ffprobe_path,
            "nvidia_smi_path": nvidia_smi_path,
            "ffmpeg_version_line": ffmpeg_ver,
            "ffprobe_version_line": ffprobe_ver,
            "gpu_query_csv": gpu_text,
        },
        "notes": [
            "FFmpeg/FFprobe are mandatory for local cinematic pipeline.",
            "GPU is optional for animatic mode, recommended for model-based generation.",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(OUT)}, ensure_ascii=False))
    return 0 if status == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

