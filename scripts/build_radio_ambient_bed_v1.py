#!/usr/bin/env python3
"""O-P31c Zone A — generate loopable ambient BED WAV (ffmpeg, no API cost)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "data" / "audio" / "seeds" / "calm_taeeum_01.example.json"
DEFAULT_OUT = ROOT / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav"
FFMPEG_BED = ROOT / "scripts" / "audio" / "ffmpeg_bed_external_generator_v1.py"


def _read_seed(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Zone A ambient BED loop WAV.")
    ap.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--out-wav", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seconds", type=float, default=0.0, help="0 = use seed target_loop_seconds")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    seed_path = args.seed_json if args.seed_json.is_absolute() else ROOT / args.seed_json
    out_wav = args.out_wav if args.out_wav.is_absolute() else ROOT / args.out_wav
    seed = _read_seed(seed_path)
    sec = float(args.seconds or seed.get("target_loop_seconds") or 120.0)
    sec = max(30.0, min(300.0, sec))

    cmd = [
        sys.executable,
        str(FFMPEG_BED),
        "--seed-json",
        str(seed_path),
        "--out-wav",
        str(out_wav),
        "--seconds",
        str(sec),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    if not out_wav.is_file():
        print("FAIL: bed wav missing", file=sys.stderr)
        return 1

    rel = out_wav.relative_to(ROOT).as_posix()
    doc = {
        "schema": "radio_ambient_bed_build_v1",
        "ok": True,
        "seed_id": seed.get("seed_id"),
        "seconds": sec,
        "path": rel,
        "license_tag": "SELF_GENERATED",
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0
    meta = out_wav.with_suffix(".meta.json")
    meta.write_text(payload + "\n", encoding="utf-8")
    print(str(out_wav))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
