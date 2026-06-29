#!/usr/bin/env py
"""B-track [HYPO] — local Supertonic TTS smoke (no Track A / no production claim)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/supertonic_tts_btrack_smoke_v1_latest.json"
OUT_WAV = ROOT / "reports/audio/supertonic_btrack_smoke_v1.wav"


def main() -> int:
    report: dict = {
        "schema": "supertonic_tts_btrack_smoke_v1",
        "lane": "b_track_hypo",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reproduce": "py scripts/smoke_supertonic_tts_btrack_v1.py",
    }
    try:
        from supertonic import TTS  # type: ignore
    except ImportError as exc:
        report.update(
            {
                "status": "skip",
                "reason": "supertonic_not_installed",
                "detail": str(exc),
                "hint": "py -m pip install supertonic",
            }
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    OUT_WAV.parent.mkdir(parents=True, exist_ok=True)
    try:
        tts = TTS(auto_download=True)
        text = "MKM 허브 나레이션 B-track 스모크입니다."
        voice_name = (tts.voice_style_names or ["M1"])[0]
        style = tts.get_voice_style(voice_name)
        wav, _aux = tts.synthesize(text, voice_style=style, lang="ko")
        tts.save_audio(wav, str(OUT_WAV))
        report.update(
            {
                "status": "ok",
                "wav_path": str(OUT_WAV.relative_to(ROOT)).replace("\\", "/"),
                "wav_bytes": OUT_WAV.stat().st_size,
                "sample_text": text,
                "voice_name": voice_name,
                "sample_rate": tts.sample_rate,
            }
        )
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 — smoke boundary
        report.update({"status": "fail", "error": str(exc)})
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
