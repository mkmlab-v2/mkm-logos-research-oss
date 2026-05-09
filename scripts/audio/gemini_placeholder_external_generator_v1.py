#!/usr/bin/env python3
"""
MKM_AUDIO_EXTERNAL_SCRIPT adapter: Gemini/Vertex seed expand → silence WAV + *.expand.json (batch merges into .meta.json).

Use when routing Google credits:
  set MKM_AUDIO_EXTERNAL_SCRIPT=scripts/audio/gemini_placeholder_external_generator_v1.py

Requires google-genai for expand unless --skip-gemini (offline silence only).
Writes *.expand.json next to out-wav; batch merges paths into .meta.json.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_billing_from_env() -> str:
    v = (os.environ.get("MKM_AUDIO_GEMINI_BILLING") or "").strip().lower()
    return v if v in ("auto", "developer", "vertex") else "developer"


def _write_silence_wav(path: Path, seconds: float, sample_rate: int = 48000) -> None:
    n = max(1, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n)


def main() -> int:
    ap = argparse.ArgumentParser(description="Gemini expand + placeholder WAV (external generator hook).")
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
    ap.add_argument("--skip-gemini", action="store_true", help="Only write silence WAV + minimal meta.")
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    expand_json = args.out_wav.with_suffix(".expand.json")
    gemini_ok = False

    if not args.skip_gemini:
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as e:
            print(json.dumps({"ok": False, "error": "gemini_expand_failed", "detail": str(e)}))
            return 5

    _write_silence_wav(args.out_wav, args.seconds, args.sample_rate)

    print(
        json.dumps(
            {
                "ok": True,
                "out_wav": str(args.out_wav.as_posix()),
                "gemini_expand_ok": gemini_ok,
                "expand_json": str(expand_json.as_posix()) if gemini_ok else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
