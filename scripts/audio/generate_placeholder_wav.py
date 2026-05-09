"""
Write a minimal PCM WAV for pipeline smoke tests (no external model).

Default: 48 kHz, 16-bit mono, silence — ideal loop seam (zero jump).
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import wave
from pathlib import Path


def _write_frames_mono16(path: Path, samples: list[int], sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buf = b"".join(struct.pack("<h", max(-32768, min(32767, s))) for s in samples)
        wf.writeframes(buf)


def build_silence(num_samples: int) -> list[int]:
    return [0] * num_samples


def build_low_sine(num_samples: int, sample_rate: int, hz: float = 220.0, amp: float = 0.05) -> list[int]:
    """Quiet sine; period-aligned segment improves seam stability when tiling."""
    out: list[int] = []
    scale = amp * 32767.0
    for i in range(num_samples):
        v = scale * math.sin(2.0 * math.pi * hz * (i / float(sample_rate)))
        out.append(int(round(v)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate placeholder mono 16-bit WAV.")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample-rate", type=int, default=48000, choices=(44100, 48000))
    ap.add_argument("--kind", choices=("silence", "low_sine"), default="silence")
    ap.add_argument("--sine-hz", type=float, default=220.0)
    args = ap.parse_args()

    n = max(1, int(args.seconds * args.sample_rate))
    if args.kind == "silence":
        samples = build_silence(n)
    else:
        samples = build_low_sine(n, args.sample_rate, hz=args.sine_hz)

    _write_frames_mono16(args.out, samples, args.sample_rate)
    print(json.dumps({"ok": True, "path": args.out.as_posix(), "samples": n, "sr": args.sample_rate}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
