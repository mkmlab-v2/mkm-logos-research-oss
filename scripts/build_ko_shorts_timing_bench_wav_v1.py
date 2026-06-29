#!/usr/bin/env python3
"""Build ~20-40s Korean shorts-style bench WAV via local Supertonic TTS [HYPO]."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_WAV = ROOT / "reports/audio/ko_shorts_timing_bench_v1.wav"
OUT_META = ROOT / "reports/ko_shorts_timing_bench_wav_v1_latest.json"
TMP_DIR = ROOT / "reports/audio/_ko_shorts_timing_bench_parts"

# Shorts-style Korean (non-clinical · education tone · enumerators for chunk stress)
PHRASES = [
    "안녕하세요. 오늘은 원내 회고 문화를 짧게 짚어 보겠습니다.",
    "첫째, 잘한 것은 매일 짧은 회고를 팀과 나누는 습관입니다.",
    "둘째, 개선할 점은 팩트 장부를 함께 점검하는 일입니다.",
    "셋째, 비난이 아니라 시스템 보완에 초점을 맞춥니다.",
    "오늘 회고 문화를 짚어 줍니다. 시청해 주셔서 감사합니다.",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.getnframes()
        return frames / float(rate) if rate > 0 else 0.0


def _synthesize_phrase(text: str, out_wav: Path) -> None:
    from supertonic import TTS  # type: ignore

    tts = TTS(auto_download=True)
    voice_name = (tts.voice_style_names or ["M1"])[0]
    style = tts.get_voice_style(voice_name)
    wav, _aux = tts.synthesize(text, voice_style=style, lang="ko")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tts.save_audio(wav, str(out_wav))


def _concat_wavs(parts: list[Path], out_wav: Path, *, pause_ms: int = 350) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    list_file = TMP_DIR / "concat_list.txt"
    lines: list[str] = []
    for i, part in enumerate(parts):
        lines.append(f"file '{part.resolve().as_posix()}'")
        if i + 1 < len(parts) and pause_ms > 0:
            silence = TMP_DIR / f"pause_{i:02d}.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=44100:cl=mono",
                    "-t",
                    f"{pause_ms / 1000.0:.3f}",
                    str(silence),
                ],
                check=True,
                capture_output=True,
            )
            lines.append(f"file '{silence.resolve().as_posix()}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )


def main() -> int:
    report: dict = {
        "schema": "ko_shorts_timing_bench_wav_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "reproduce": "py scripts/build_ko_shorts_timing_bench_wav_v1.py",
    }
    try:
        from supertonic import TTS  # type: ignore  # noqa: F401
    except ImportError as exc:
        report.update({"ok": False, "status": "skip", "error": "supertonic_not_installed", "detail": str(exc)})
        OUT_META.parent.mkdir(parents=True, exist_ok=True)
        OUT_META.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    if TMP_DIR.exists():
        for p in TMP_DIR.glob("*.wav"):
            p.unlink(missing_ok=True)
    else:
        TMP_DIR.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    for idx, phrase in enumerate(PHRASES, start=1):
        part = TMP_DIR / f"phrase_{idx:02d}.wav"
        _synthesize_phrase(phrase, part)
        parts.append(part)

    _concat_wavs(parts, OUT_WAV, pause_ms=400)
    duration_sec = round(_wav_duration_sec(OUT_WAV), 3)
    report.update(
        {
            "ok": True,
            "status": "ok",
            "generated_at_utc": _utc_now(),
            "wav_path": _rel(OUT_WAV),
            "wav_bytes": OUT_WAV.stat().st_size,
            "duration_sec": duration_sec,
            "phrase_count": len(PHRASES),
            "phrases": PHRASES,
        }
    )
    OUT_META.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wav_path": _rel(OUT_WAV), "duration_sec": duration_sec}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
