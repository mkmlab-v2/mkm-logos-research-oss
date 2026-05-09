#!/usr/bin/env python3
"""
MKM_AUDIO_EXTERNAL_SCRIPT adapter: Gemini seed expand → mono tone WAV (hint-aware).

Same CLI as `gemini_placeholder_external_generator_v1.py` / `tone_external_generator_v1.py`.
Unless `--skip-expand`, runs `gemini_bgm_seed_expand_v1.py` first (honours `MKM_AUDIO_EXPAND_DRY_RUN`
for API-free dry runs). Then writes a Hann-envelope sine bed using:

- `suggested_bpm_range` midpoint → carrier Hz (when expand JSON exists)
- `suggested_duration_sec` → clip length when within bounds
- Fallbacks match `tone_external_generator_v1.py`
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_billing_from_env() -> str:
    v = (os.environ.get("MKM_AUDIO_GEMINI_BILLING") or "").strip().lower()
    return v if v in ("auto", "developer", "vertex") else "developer"


def _hz_from_seed(seed: dict[str, Any]) -> float:
    bpm = float(seed.get("bpm") or 72.0)
    base = 55.0 + (bpm % 37) * 2.0
    return min(max(base, 55.0), 880.0)


def _hz_from_expand(seed: dict[str, Any], expand: dict[str, Any] | None) -> float:
    if expand and isinstance(expand.get("suggested_bpm_range"), list):
        r = expand["suggested_bpm_range"]
        if len(r) >= 2:
            mid = (float(r[0]) + float(r[1])) / 2.0
            base = 55.0 + (mid % 37) * 2.0
            return min(max(base, 55.0), 880.0)
    return _hz_from_seed(seed)


def _seconds_from_expand(cli_seconds: float, expand: dict[str, Any] | None) -> float:
    if expand:
        d = expand.get("suggested_duration_sec")
        if isinstance(d, (int, float)):
            v = float(d)
            if 0.5 <= v <= 120.0:
                return v
    return cli_seconds


def _write_tone_wav(path: Path, seconds: float, hz: float, sample_rate: int = 48000) -> None:
    n = max(2, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    amp = 6000.0
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
    ap = argparse.ArgumentParser(description="Gemini expand + hint-aware tone WAV.")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-wav", type=Path, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample-rate", type=int, default=48000)
    ap.add_argument(
        "--billing",
        choices=("auto", "developer", "vertex"),
        default=_default_billing_from_env(),
    )
    ap.add_argument(
        "--model",
        default=os.environ.get("MKM_AUDIO_GEMINI_MODEL", "gemini-2.5-flash"),
    )
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument(
        "--skip-expand",
        action="store_true",
        help="Do not run Gemini expand; tone from seed only (same as tone_external_generator_v1).",
    )
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    seed = json.loads(args.seed_json.read_text(encoding="utf-8"))
    if not isinstance(seed, dict):
        seed = {}

    expand_json = args.out_wav.with_suffix(".expand.json")
    expand_doc: dict[str, Any] | None = None
    gemini_ok = False

    if not args.skip_expand:
        cmd = [
            sys.executable,
            str(_REPO_ROOT / "scripts/audio/gemini_bgm_seed_expand_v1.py"),
            "--seed-json",
            str(args.seed_json.resolve()),
            "--out-json",
            str(expand_json.resolve()),
            "--billing",
            args.billing,
            "--model",
            args.model,
            "--timeout",
            str(args.timeout),
        ]
        if os.environ.get("MKM_AUDIO_EXPAND_DRY_RUN", "").strip().lower() in ("1", "true", "yes"):
            cmd.append("--dry-run")
        try:
            subprocess.run(cmd, check=True, cwd=str(_REPO_ROOT), timeout=max(args.timeout + 30, 150))
            gemini_ok = expand_json.is_file()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            print(json.dumps({"ok": False, "error": "gemini_expand_failed", "detail": str(e)}))
            return 5
        if gemini_ok:
            try:
                expand_doc = json.loads(expand_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                expand_doc = None

    hz = _hz_from_expand(seed, expand_doc)
    sec = _seconds_from_expand(args.seconds, expand_doc)
    _write_tone_wav(args.out_wav, sec, hz, args.sample_rate)

    print(
        json.dumps(
            {
                "ok": True,
                "generator": "expand_tone_external_generator_v1",
                "out_wav": str(args.out_wav.as_posix()),
                "hz": hz,
                "seconds": sec,
                "gemini_expand_ok": gemini_ok,
                "expand_json": str(expand_json.as_posix()) if gemini_ok else None,
                "index": args.index,
                "run_id": args.run_id,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
