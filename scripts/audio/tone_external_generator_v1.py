#!/usr/bin/env python3
"""
Offline external generator: mono sine bed + Hann-like envelope (edges at zero).

Same CLI contract as `external_generator_stub_v1.py`. No cloud calls — use for
auditioning non-silence audio while keeping the batch harness unchanged.

Envelope zeros sample[0] and sample[n-1] so loop seam jump stays small vs gate defaults.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import wave
from pathlib import Path


def _hz_from_seed(seed: dict) -> float:
    bpm = float(seed.get("bpm") or 72.0)
    # Spread fundamentals without magic tables (audition-friendly)
    base = 55.0 + (bpm % 37) * 2.0
    return min(max(base, 55.0), 880.0)


def _write_tone_wav(path: Path, seconds: float, hz: float, sample_rate: int = 48000) -> None:
    n = max(2, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    amp = 6000.0  # keep headroom in int16
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        denom = max(1.0, float(n - 1))
        for i in range(n):
            env = math.sin(math.pi * i / denom)
            s = amp * env * math.sin(2.0 * math.pi * hz * (i / float(sample_rate)))
            v = int(max(-32767, min(32767, round(s))))
            wf.writeframes(struct.pack("<h", v))


def main() -> int:
    ap = argparse.ArgumentParser(description="Tone external BGM generator (stdlib WAV, no cloud).")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-wav", type=Path, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample-rate", type=int, default=48000)
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    seed = json.loads(args.seed_json.read_text(encoding="utf-8"))
    hz = _hz_from_seed(seed if isinstance(seed, dict) else {})
    _write_tone_wav(args.out_wav, args.seconds, hz, args.sample_rate)
    print(
        json.dumps(
            {
                "ok": True,
                "generator": "tone_external_generator_v1",
                "out_wav": str(args.out_wav.as_posix()),
                "hz": hz,
                "index": args.index,
                "run_id": args.run_id,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
