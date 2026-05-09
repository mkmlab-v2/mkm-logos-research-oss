#!/usr/bin/env python3
"""
MKM_AUDIO_EXTERNAL_SCRIPT: ffmpeg lavfi colored-noise bed → mono 48k s16 WAV.

Default noise color is **brown**; when `expanded_prompt_*` text exists, SHA-256 picks
**brown / pink / white** deterministically (spectral tilt variety).

Reads optional `OUT.expand.json` (same stem as `--out-wav`) for duration hints,
`suggested_bpm_range`, and **`expanded_prompt_en` / `expanded_prompt_ko`**.

When non-empty prompts exist, a SHA-256 of their concatenation **deterministically**
adjusts filter bands, volume (lavfi path), and carrier Hz (tone fallback) — same seed
+ same expand text ⇒ same audio stats (audit-friendly digest in stdout JSON).

If `ffmpeg` is missing or fails, falls back to the same Hann sine bed as
`tone_external_generator_v1.py` (stdlib WAV; no subprocess).

Optional env: `MKM_AUDIO_FFMPEG` — explicit ffmpeg executable path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _clamp_seconds(x: float) -> float:
    return max(0.5, min(120.0, float(x)))


def _load_expand(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _effective_seconds(cli_seconds: float, expand: dict[str, Any] | None) -> float:
    if expand:
        d = expand.get("suggested_duration_sec")
        if isinstance(d, (int, float)):
            v = float(d)
            if 0.5 <= v <= 120.0:
                return v
    return _clamp_seconds(cli_seconds)


def _band_edges_hz(seed: dict[str, Any], expand: dict[str, Any] | None) -> tuple[float, float, float]:
    """Return (highpass_hz, lowpass_hz, volume_linear)."""
    bpm = float(seed.get("bpm") or 72.0)
    if expand and isinstance(expand.get("suggested_bpm_range"), list):
        r = expand["suggested_bpm_range"]
        if len(r) >= 2:
            bpm = (float(r[0]) + float(r[1])) / 2.0
    mid = 280.0 + (bpm % 72.0) * 8.0
    hp = max(120.0, mid - 220.0)
    lp = min(2800.0, mid + 480.0)
    sid = str(seed.get("seed_id", "seed"))
    h = int(hashlib.sha256(sid.encode("utf-8")).hexdigest()[:8], 16)
    vol = 0.07 + (h % 9000) / 100000.0
    return hp, lp, round(vol, 4)


def _prompt_text_for_hash(expand: dict[str, Any] | None) -> str | None:
    if not expand:
        return None
    en = str(expand.get("expanded_prompt_en") or "").strip()
    ko = str(expand.get("expanded_prompt_ko") or "").strip()
    if not en and not ko:
        return None
    return (en + "\n" + ko).strip()


def _expand_prompt_audit(expand: dict[str, Any] | None) -> dict[str, Any]:
    blob = _prompt_text_for_hash(expand)
    if not blob:
        return {"expand_prompt_influence": False}
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return {"expand_prompt_influence": True, "prompt_digest16": digest[:16]}


def _prompt_adjust_edges(
    hp: float, lp: float, vol: float, expand: dict[str, Any] | None
) -> tuple[float, float, float]:
    blob = _prompt_text_for_hash(expand)
    if not blob:
        return hp, lp, vol
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    u = int(digest[:12], 16)
    dhp = (u % 241) - 120
    dlp = ((u >> 8) % 501) - 250
    dvol = (((u >> 20) % 801) / 10000.0) - 0.04
    nhp = max(60.0, hp + dhp)
    nlp = min(8000.0, lp + dlp)
    if nhp >= nlp - 100.0:
        nlp = nhp + 150.0
    nvol = min(0.25, max(0.05, vol + dvol))
    return round(nhp, 2), round(nlp, 2), round(nvol, 4)


def _hz_tone_with_prompt(seed: dict[str, Any], expand: dict[str, Any] | None) -> float:
    from scripts.audio.tone_external_generator_v1 import _hz_from_seed

    hz = _hz_from_seed(seed)
    blob = _prompt_text_for_hash(expand)
    if not blob:
        return hz
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    u = int(digest[8:16], 16)
    delta = (u % 81) - 40
    return min(880.0, max(55.0, hz + delta))


def _noise_color_lavfi(expand: dict[str, Any] | None) -> str:
    """ffmpeg anoisesrc color=brown|pink|white — prompt-hash picks when prompts exist."""
    colors = ("brown", "pink", "white")
    blob = _prompt_text_for_hash(expand)
    if not blob:
        return "brown"
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    idx = int(digest[10:12], 16) % len(colors)
    return colors[idx]


def _find_ffmpeg(cli_binary: str | None) -> str | None:
    if cli_binary:
        p = Path(cli_binary)
        if p.is_file():
            return str(p.resolve())
        w = shutil.which(cli_binary)
        return w
    env = (os.environ.get("MKM_AUDIO_FFMPEG") or "").strip()
    if env:
        pe = Path(env)
        if pe.is_file():
            return str(pe.resolve())
        we = shutil.which(env)
        if we:
            return we
    return shutil.which("ffmpeg")


def _run_ffmpeg_bed(
    ffmpeg_bin: str,
    out_wav: Path,
    seconds: float,
    sample_rate: int,
    hp: float,
    lp: float,
    vol: float,
    noise_color: str,
) -> subprocess.CompletedProcess[str]:
    # lavfi colored noise + band limiting; output PCM WAV mono.
    dur = _clamp_seconds(seconds)
    nc = noise_color if noise_color in ("brown", "pink", "white") else "brown"
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anoisesrc=color={nc}:sample_rate={sample_rate}",
        "-af",
        f"highpass=f={hp:.1f},lowpass=f={lp:.1f},volume={vol:.4f}",
        "-t",
        f"{dur:.3f}",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        "s16",
        str(out_wav),
    ]
    return subprocess.run(
        cmd,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=max(30, int(dur) + 20),
    )


def _write_tone_fallback(
    args: argparse.Namespace, seed: dict[str, Any], seconds: float, hz: float
) -> None:
    from scripts.audio.tone_external_generator_v1 import _write_tone_wav

    _write_tone_wav(args.out_wav, seconds, hz, args.sample_rate)


def main() -> int:
    ap = argparse.ArgumentParser(description="ffmpeg lavfi colored-noise bed WAV (tone fallback).")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--out-wav", type=Path, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--sample-rate", type=int, default=48000)
    ap.add_argument(
        "--ffmpeg-binary",
        default="",
        help="Override ffmpeg path (else PATH / MKM_AUDIO_FFMPEG).",
    )
    ap.add_argument(
        "--force-tone-fallback",
        action="store_true",
        help="Skip ffmpeg; run tone_external_generator only (debug/offline).",
    )
    args = ap.parse_args()

    if not args.seed_json.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    seed = json.loads(args.seed_json.read_text(encoding="utf-8"))
    if not isinstance(seed, dict):
        seed = {}

    expand_path = args.out_wav.with_suffix(".expand.json")
    expand_doc = _load_expand(expand_path)
    sec = _effective_seconds(args.seconds, expand_doc)
    hp0, lp0, vol0 = _band_edges_hz(seed, expand_doc)
    hp, lp, vol = _prompt_adjust_edges(hp0, lp0, vol0, expand_doc)
    prompt_audit = _expand_prompt_audit(expand_doc)
    tone_hz = _hz_tone_with_prompt(seed, expand_doc)
    seed_id = str(seed.get("seed_id", "unknown"))
    noise_color = _noise_color_lavfi(expand_doc)

    if args.force_tone_fallback:
        _write_tone_fallback(args, seed, sec, tone_hz)
        print(
            json.dumps(
                {
                    "ok": True,
                    **prompt_audit,
                    "generator": "ffmpeg_bed_external_generator_v1",
                    "backend": "tone_fallback",
                    "reason": "force_tone_fallback",
                    "seed_id": seed_id,
                    "hz": tone_hz,
                    "seconds": sec,
                    "expand_json_seen": expand_path.is_file(),
                    "index": args.index,
                    "run_id": args.run_id,
                    "out_wav": str(args.out_wav.as_posix()),
                },
                ensure_ascii=False,
            )
        )
        return 0

    ff = _find_ffmpeg(args.ffmpeg_binary.strip() or None)
    if not ff:
        _write_tone_fallback(args, seed, sec, tone_hz)
        print(
            json.dumps(
                {
                    "ok": True,
                    **prompt_audit,
                    "generator": "ffmpeg_bed_external_generator_v1",
                    "backend": "tone_fallback",
                    "reason": "ffmpeg_not_found",
                    "seed_id": seed_id,
                    "hz": tone_hz,
                    "seconds": sec,
                    "expand_json_seen": expand_path.is_file(),
                    "index": args.index,
                    "run_id": args.run_id,
                    "out_wav": str(args.out_wav.as_posix()),
                },
                ensure_ascii=False,
            )
        )
        return 0

    args.out_wav.parent.mkdir(parents=True, exist_ok=True)
    proc = _run_ffmpeg_bed(ff, args.out_wav, sec, args.sample_rate, hp, lp, vol, noise_color)
    if proc.returncode != 0 or not args.out_wav.is_file():
        err = (proc.stderr or proc.stdout or "").strip()[:500]
        _write_tone_fallback(args, seed, sec, tone_hz)
        print(
            json.dumps(
                {
                    "ok": True,
                    **prompt_audit,
                    "generator": "ffmpeg_bed_external_generator_v1",
                    "backend": "tone_fallback",
                    "reason": "ffmpeg_failed",
                    "ffmpeg_stderr": err,
                    "seed_id": seed_id,
                    "hz": tone_hz,
                    "seconds": sec,
                    "highpass_hz": hp,
                    "lowpass_hz": lp,
                    "volume": vol,
                    "noise_color": noise_color,
                    "expand_json_seen": expand_path.is_file(),
                    "index": args.index,
                    "run_id": args.run_id,
                    "out_wav": str(args.out_wav.as_posix()),
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "ok": True,
                **prompt_audit,
                "generator": "ffmpeg_bed_external_generator_v1",
                "backend": "ffmpeg_lavfi",
                "ffmpeg": ff,
                "out_wav": str(args.out_wav.as_posix()),
                "seed_id": seed_id,
                "seconds": sec,
                "highpass_hz": hp,
                "lowpass_hz": lp,
                "volume": vol,
                "noise_color": noise_color,
                "expand_json_seen": expand_path.is_file(),
                "index": args.index,
                "run_id": args.run_id,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
