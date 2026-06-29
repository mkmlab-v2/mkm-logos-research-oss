#!/usr/bin/env python3
"""P1 spike: aligned word timing vs proportional baseline for Korean shorts STT [HYPO]."""

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

from scripts.ko_shorts_stt_timing_lib_v1 import (  # noqa: E402
    build_timing_spike_report_v1,
    chunk_aligned_words_v1,
    extract_whisper_aligned_words_v1,
    format_srt_v1,
    segments_proportional_from_words_v1,
    whisper_segments_without_words_v1,
)
from scripts.ko_shorts_subtitle_gate_lib_v1 import (  # noqa: E402
    PROFILES,
    evaluate_subtitle_gate_v1,
    refine_segments_for_profile_v1,
)
from scripts.media_stt_transcription_lib_v1 import refine_stt_segments_semantic_ko_v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ko_shorts_stt_timing_spike_v1_latest.json"
DEFAULT_SRT = ROOT / "reports/ko_shorts_stt_timing_spike_v1_latest.srt"
DEFAULT_WORDS_FIXTURE = ROOT / "tests/fixtures/ko_shorts_aligned_words_spike_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _apply_subtitle_profile_v1(
    report: dict[str, Any],
    *,
    profile_key: str | None,
) -> dict[str, Any]:
    if not profile_key:
        return report
    profile = PROFILES[profile_key]
    base = list(report.get("p1_segments") or [])
    subtitle_segments = refine_segments_for_profile_v1(base, profile, two_pass=True)
    gate = evaluate_subtitle_gate_v1(subtitle_segments, profile)
    report["subtitle_profile"] = profile.key
    report["subtitle_profile_label"] = profile.label
    report["max_chars"] = profile.max_chars
    report["subtitle_segments"] = subtitle_segments
    report["subtitle_segment_count"] = len(subtitle_segments)
    report["subtitle_gate"] = gate
    return report


def run_spike_from_words(
    words: list[dict[str, Any]],
    *,
    wav_source: str,
    stt_engine: str,
    model_name: str,
    pause_gap_sec: float,
    max_chars: int,
    min_seg_sec: float,
    subtitle_profile: str | None = None,
) -> dict[str, Any]:
    p1_segments = chunk_aligned_words_v1(
        words,
        max_chars=max_chars,
        pause_gap_sec=pause_gap_sec,
        min_seg_sec=min_seg_sec,
    )
    p0_segments = segments_proportional_from_words_v1(words, min_seg_sec=min_seg_sec)
    report = build_timing_spike_report_v1(
        wav_source=wav_source,
        words=words,
        p0_segments=p0_segments,
        p1_segments=p1_segments,
        stt_engine=stt_engine,
        model_name=model_name,
        pause_gap_sec=pause_gap_sec,
        max_chars=max_chars,
    )
    return _apply_subtitle_profile_v1(report, profile_key=subtitle_profile)


def run_spike_from_wav(
    wav: Path,
    *,
    model_name: str,
    beam_size: int,
    language: str,
    pause_gap_sec: float,
    max_chars: int,
    min_seg_sec: float,
    subtitle_profile: str | None = None,
) -> dict[str, Any]:
    words = extract_whisper_aligned_words_v1(
        wav,
        model_name=model_name,
        beam_size=beam_size,
        language=language,
    )
    p1_segments = chunk_aligned_words_v1(
        words,
        max_chars=max_chars,
        pause_gap_sec=pause_gap_sec,
        min_seg_sec=min_seg_sec,
    )
    whisper_segs = whisper_segments_without_words_v1(
        wav,
        model_name=model_name,
        beam_size=beam_size,
        language=language,
    )
    p0_segments = refine_stt_segments_semantic_ko_v1(whisper_segs)
    report = build_timing_spike_report_v1(
        wav_source=_rel(wav),
        words=words,
        p0_segments=p0_segments,
        p1_segments=p1_segments,
        stt_engine=f"faster_whisper:aligned:{model_name}",
        model_name=model_name,
        pause_gap_sec=pause_gap_sec,
        max_chars=max_chars,
    )
    report["p0_mode"] = "whisper_segment_proportional_semantic"
    return _apply_subtitle_profile_v1(report, profile_key=subtitle_profile)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wav", type=Path, default=None)
    ap.add_argument("--from-words-json", type=Path, default=None, help="offline fixture; skips whisper")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--srt-out", type=Path, default=DEFAULT_SRT)
    ap.add_argument("--model", default="small")
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--language", default="ko")
    ap.add_argument("--pause-gap-sec", type=float, default=0.4)
    ap.add_argument("--max-chars", type=int, default=28)
    ap.add_argument("--min-seg-sec", type=float, default=0.5)
    ap.add_argument(
        "--subtitle-profile",
        choices=list(PROFILES),
        default=None,
        help="optional: refine p1 -> subtitle_segments + gate (netflix_v16|shorts_v28)",
    )
    args = ap.parse_args()

    profile_key = args.subtitle_profile
    chunk_max_chars = PROFILES[profile_key].max_chars if profile_key else args.max_chars

    if args.from_words_json:
        src = args.from_words_json if args.from_words_json.is_absolute() else ROOT / args.from_words_json
        if not src.is_file():
            src = DEFAULT_WORDS_FIXTURE
        doc = _read_json(src)
        words = list(doc.get("words") or [])
        report = run_spike_from_words(
            words,
            wav_source=str(doc.get("wav_source") or _rel(src)),
            stt_engine=str(doc.get("stt_engine") or "fixture:aligned_words"),
            model_name=str(doc.get("model_name") or args.model),
            pause_gap_sec=float(doc.get("pause_gap_sec") or args.pause_gap_sec),
            max_chars=chunk_max_chars,
            min_seg_sec=float(doc.get("min_seg_sec") or args.min_seg_sec),
            subtitle_profile=profile_key,
        )
    elif args.wav:
        wav = args.wav if args.wav.is_absolute() else ROOT / args.wav
        if not wav.is_file():
            print(json.dumps({"ok": False, "error": "wav_missing", "path": str(wav)}), file=sys.stderr)
            return 1
        report = run_spike_from_wav(
            wav,
            model_name=args.model,
            beam_size=args.beam_size,
            language=args.language,
            pause_gap_sec=args.pause_gap_sec,
            max_chars=chunk_max_chars,
            min_seg_sec=args.min_seg_sec,
            subtitle_profile=profile_key,
        )
    else:
        src = DEFAULT_WORDS_FIXTURE
        if not src.is_file():
            print(json.dumps({"ok": False, "error": "need_wav_or_fixture"}), file=sys.stderr)
            return 1
        doc = _read_json(src)
        words = list(doc.get("words") or [])
        report = run_spike_from_words(
            words,
            wav_source=str(doc.get("wav_source") or _rel(src)),
            stt_engine=str(doc.get("stt_engine") or "fixture:aligned_words"),
            model_name=str(doc.get("model_name") or args.model),
            pause_gap_sec=args.pause_gap_sec,
            max_chars=chunk_max_chars,
            min_seg_sec=args.min_seg_sec,
            subtitle_profile=profile_key,
        )

    report["generated_at_utc"] = _utc_now()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    srt_out = args.srt_out if args.srt_out.is_absolute() else ROOT / args.srt_out
    out.parent.mkdir(parents=True, exist_ok=True)
    srt_segments = list(report.get("subtitle_segments") or report.get("p1_segments") or [])
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    srt_out.write_text(format_srt_v1(srt_segments), encoding="utf-8")

    summary = {
        "ok": True,
        "out": _rel(out),
        "srt_out": _rel(srt_out),
        "aligned_word_count": report.get("aligned_word_count"),
        "p1_segment_count": report.get("p1_segment_count"),
        "subtitle_segment_count": report.get("subtitle_segment_count"),
        "subtitle_profile": report.get("subtitle_profile"),
        "subtitle_gate_pass": (report.get("subtitle_gate") or {}).get("gate_pass"),
        "timing_authority_p1": report.get("timing_authority_p1"),
        "drift_vs_proportional": report.get("drift_vs_proportional"),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
