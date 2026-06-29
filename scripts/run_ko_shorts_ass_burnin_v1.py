#!/usr/bin/env python3
"""Build ASS safe-area subs and optional ffmpeg burn-in for ko shorts STT [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_ass_burnin_lib_v1 import (  # noqa: E402
    burn_ass_into_vertical_video_v1,
    segments_from_srt_v1,
    write_sidecars_from_segments_v1,
)
from scripts.ko_shorts_subtitle_gate_lib_v1 import (  # noqa: E402
    PROFILE_NETFLIX_V16,
    PROFILE_SHORTS_V28,
    PROFILES,
    evaluate_subtitle_gate_v1,
    refine_segments_for_profile_v1,
)

DEFAULT_SPIKE = ROOT / "reports/ko_shorts_stt_timing_web_deeply_v1_latest.json"
DEFAULT_WAV = ROOT / "reports/audio/ko_shorts_web_deeply_read_v1.wav"
DEFAULT_ASS = ROOT / "reports/ko_shorts_burnin_web_deeply_v1_latest.ass"
DEFAULT_MP4 = ROOT / "reports/ko_shorts_burnin_web_deeply_v1_latest.mp4"
DEFAULT_META = ROOT / "reports/ko_shorts_burnin_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spike-json", type=Path, default=DEFAULT_SPIKE)
    ap.add_argument("--wav", type=Path, default=DEFAULT_WAV)
    ap.add_argument("--profile", choices=list(PROFILES), default=PROFILE_NETFLIX_V16)
    ap.add_argument("--ass-out", type=Path, default=DEFAULT_ASS)
    ap.add_argument("--srt-out", type=Path, default=None)
    ap.add_argument("--mp4-out", type=Path, default=DEFAULT_MP4)
    ap.add_argument("--meta-out", type=Path, default=DEFAULT_META)
    ap.add_argument("--skip-burn", action="store_true")
    ap.add_argument("--srt-in", type=Path, default=None, help="optional SRT instead of spike json")
    args = ap.parse_args()

    profile = PROFILES[args.profile]
    if args.srt_in:
        srt_path = args.srt_in if args.srt_in.is_absolute() else ROOT / args.srt_in
        segments = segments_from_srt_v1(srt_path.read_text(encoding="utf-8-sig"))
        wav_source = _rel(srt_path)
    else:
        spike = args.spike_json if args.spike_json.is_absolute() else ROOT / args.spike_json
        doc = _read_json(spike)
        base = list(doc.get("p1_segments") or doc.get("p0_segments") or [])
        segments = refine_segments_for_profile_v1(base, profile)
        wav_source = str(doc.get("wav_source") or _rel(spike))

    gate = evaluate_subtitle_gate_v1(segments, profile)
    ass_out = args.ass_out if args.ass_out.is_absolute() else ROOT / args.ass_out
    srt_out = args.srt_out if args.srt_out and args.srt_out.is_absolute() else (
        (ROOT / args.srt_out) if args.srt_out else ass_out.with_suffix(".srt")
    )
    write_sidecars_from_segments_v1(segments, ass_path=ass_out, srt_path=srt_out, profile_key=profile.key)

    wav = args.wav if args.wav.is_absolute() else ROOT / args.wav
    mp4_out = args.mp4_out if args.mp4_out.is_absolute() else ROOT / args.mp4_out
    burned = False
    burn_error: str | None = None
    if not args.skip_burn:
        if not wav.is_file():
            burn_error = "wav_missing"
        else:
            try:
                burn_ass_into_vertical_video_v1(wav_path=wav, ass_path=ass_out, out_mp4=mp4_out)
                burned = True
            except Exception as exc:  # noqa: BLE001
                burn_error = f"{exc.__class__.__name__}:{exc}"

    meta = {
        "schema": "ko_shorts_burnin_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "profile": profile.key,
        "wav_source": _rel(wav) if wav.is_file() else str(wav),
        "spike_or_srt_source": wav_source,
        "segment_count": len(segments),
        "gate": gate,
        "ass_path": _rel(ass_out),
        "srt_path": _rel(srt_out),
        "mp4_path": _rel(mp4_out) if burned else None,
        "burned": burned,
        "burn_error": burn_error,
        "reproduce": "py scripts/run_ko_shorts_ass_burnin_v1.py",
    }
    meta_out = args.meta_out if args.meta_out.is_absolute() else ROOT / args.meta_out
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": burned or args.skip_burn,
                "profile": profile.key,
                "gate_pass": gate.get("gate_pass"),
                "ass_path": _rel(ass_out),
                "mp4_path": meta.get("mp4_path"),
                "burned": burned,
                "burn_error": burn_error,
            },
            ensure_ascii=False,
        )
    )
    return 0 if (burned or args.skip_burn) else 1


if __name__ == "__main__":
    raise SystemExit(main())
