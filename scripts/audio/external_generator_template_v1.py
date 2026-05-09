#!/usr/bin/env python3
"""
Starter for a real `MKM_AUDIO_EXTERNAL_SCRIPT` implementation.

Copy this file (keep name or rename outside repo), wire your model/API, and point:

  set MKM_AUDIO_EXTERNAL_SCRIPT=scripts/audio/your_generator.py

Contract (invoked by `run_bgm_generation_batch.py --emit external`):

  --seed-json PATH   (required)  MKM seed JSON, same path for every index in a batch
  --out-wav PATH     (required)  mono 16-bit PCM WAV to write
  --index N          batch row index (0-based)
  --run-id STR       batch correlation id
  --seconds FLOAT    target duration hint
  --sample-rate INT  default 48000

Optional: if you run the Gemini chain first (`gemini_placeholder_external_generator_v1.py`),
the expand sidecar is written next to the WAV: `out_wav` stem + `.expand.json`
(e.g. `bgm_run_000.expand.json`). Read `expanded_prompt_en` / `expanded_prompt_ko` there.

Default behavior below is silence WAV (no network) so CI and local smoke stay deterministic.
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
    ap = argparse.ArgumentParser(description="Template external BGM generator (silence default).")
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

    seed = json.loads(args.seed_json.read_text(encoding="utf-8"))
    seed_id = str(seed.get("seed_id", "unknown"))
    expand_path = args.out_wav.with_suffix(".expand.json")
    expand_prompt: str | None = None
    if expand_path.is_file():
        try:
            exp = json.loads(expand_path.read_text(encoding="utf-8"))
            expand_prompt = exp.get("expanded_prompt_en") or exp.get("expanded_prompt_ko")
        except (json.JSONDecodeError, OSError):
            pass

    # TODO: replace with synthesis — use `seed`, `expand_prompt`, `args.seconds`, etc.

    _write_silence_wav(args.out_wav, args.seconds, args.sample_rate)
    print(
        json.dumps(
            {
                "ok": True,
                "seed_id": seed_id,
                "out_wav": str(args.out_wav.as_posix()),
                "index": args.index,
                "run_id": args.run_id,
                "expand_json_seen": expand_path.is_file(),
                "expand_prompt_preview": (expand_prompt[:120] + "…")
                if expand_prompt and len(expand_prompt) > 120
                else expand_prompt,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
