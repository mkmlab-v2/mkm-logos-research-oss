#!/usr/bin/env python3
"""Download allowlisted YouTube audio clip as 16kHz mono WAV [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = ROOT / "tests/fixtures/ko_shorts_clinical_sim_youtube_allowlist_v1.json"
DEFAULT_OUT = ROOT / "reports/audio/ko_shorts_web_youtube_edu_v1.wav"
DEFAULT_META = ROOT / "reports/ko_shorts_web_speech_youtube_edu_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        return wf.getnframes() / float(rate) if rate > 0 else 0.0


def _to_16k_mono(in_wav: Path, out_wav: Path) -> None:
    if shutil.which("ffmpeg") is None:
        if in_wav.resolve() != out_wav.resolve():
            shutil.copyfile(in_wav, out_wav)
        return
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(in_wav),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )


def fetch_youtube_clip_wav_v1(
    ssot: dict[str, Any],
    *,
    out_wav: Path,
    out_meta: Path | None = None,
) -> dict[str, Any]:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("yt-dlp not installed") from exc

    url = str(ssot.get("youtube_url") or "").strip()
    if not url:
        raise RuntimeError("youtube_url missing in ssot")

    start = float(ssot.get("clip_start_sec") or 0.0)
    duration = float(ssot.get("clip_duration_sec") or 25.0)
    end = start + duration
    if duration <= 0:
        raise RuntimeError("clip_duration_sec must be > 0")

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_base = out_wav.parent / f"_yt_clip_{ssot.get('video_id') or 'tmp'}"
    tmp_wav = tmp_base.with_suffix(".wav")

    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(tmp_base) + ".%(ext)s",
        "download_ranges": yt_dlp.utils.download_range_func(None, [(start, end)]),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if not tmp_wav.is_file():
        candidates = sorted(out_wav.parent.glob(f"_yt_clip_{ssot.get('video_id') or '*'}*.wav"))
        if not candidates:
            raise RuntimeError("yt-dlp did not produce wav output")
        tmp_wav = candidates[0]

    _to_16k_mono(tmp_wav, out_wav)
    for p in out_wav.parent.glob(f"_yt_clip_{ssot.get('video_id') or '*'}*"):
        if p.is_file() and p.resolve() != out_wav.resolve():
            p.unlink(missing_ok=True)

    report = {
        "schema": "ko_shorts_web_speech_fetch_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "not_patient_data": True,
        "clinical_sim": bool(ssot.get("clinical_sim", True)),
        "proxy_tier": str(ssot.get("proxy_tier") or "education_allowlist"),
        "ok": True,
        "generated_at_utc": _utc_now(),
        "source": "youtube_edu",
        "wav_path": _rel(out_wav),
        "wav_bytes": out_wav.stat().st_size,
        "duration_sec": round(_wav_duration_sec(out_wav), 3),
        "youtube_url": url,
        "video_id": ssot.get("video_id"),
        "clip_start_sec": start,
        "clip_duration_sec": duration,
        "title": ssot.get("title"),
        "license": ssot.get("license_note"),
        "source_page": url,
        "allowlist_ssot": _rel(DEFAULT_SSOT),
        "reproduce": "py scripts/fetch_youtube_audio_clip_wav_v1.py",
    }
    if out_meta is not None:
        out_meta.parent.mkdir(parents=True, exist_ok=True)
        out_meta.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssot", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--out-wav", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    args = ap.parse_args()

    ssot_path = args.ssot if args.ssot.is_absolute() else ROOT / args.ssot
    out_wav = args.out_wav if args.out_wav.is_absolute() else ROOT / args.out_wav
    out_meta = args.out_meta if args.out_meta.is_absolute() else ROOT / args.out_meta
    if not ssot_path.is_file():
        print(json.dumps({"ok": False, "error": "ssot_missing", "path": _rel(ssot_path)}), file=sys.stderr)
        return 1

    report = fetch_youtube_clip_wav_v1(_read_json(ssot_path), out_wav=out_wav, out_meta=out_meta)
    print(
        json.dumps(
            {
                "ok": True,
                "wav_path": report["wav_path"],
                "duration_sec": report["duration_sec"],
                "video_id": report.get("video_id"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
