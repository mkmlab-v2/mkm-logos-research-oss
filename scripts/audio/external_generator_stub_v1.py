#!/usr/bin/env python3
"""
Reference implementation for MKM_AUDIO_EXTERNAL_SCRIPT.

Writes the same silence WAV as the built-in placeholder (no cloud cost).
Replace this script with your own generator that honors the CLI contract.
"""

from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path


def _write_silence_wav(path: Path, seconds: float, sample_rate: int = 48000) -> None:
    n = max(1, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n)


def main() -> int:
    ap = argparse.ArgumentParser(description="Stub external BGM generator (silence WAV).")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-wav", type=Path, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample-rate", type=int, default=48000)
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(f"seed-json not found: {args.seed_json}")
        return 2

    _ = json.loads(args.seed_json.read_text(encoding="utf-8"))
    _write_silence_wav(args.out_wav, args.seconds, args.sample_rate)
    print(
        json.dumps(
            {
                "ok": True,
                "generator": "external_generator_stub_v1",
                "out_wav": str(args.out_wav.as_posix()),
                "index": args.index,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
