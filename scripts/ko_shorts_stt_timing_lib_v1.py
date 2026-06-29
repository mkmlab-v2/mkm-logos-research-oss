#!/usr/bin/env python3
"""P1 Korean shorts STT timing — aligned word tokens as SSOT [HYPO]."""

from __future__ import annotations

import re
from typing import Any

from scripts.media_stt_transcription_lib_v1 import (
    _is_orphan_ending,
    _is_orphan_prefix,
    format_timestamp,
    parse_timestamp_seconds,
    refine_stt_segments_semantic_ko_v1,
    split_transcript_proportional_segments,
)

TIMING_AUTHORITY_ALIGNED = "aligned_token"
TIMING_AUTHORITY_PROPORTIONAL = "proportional_fallback"


def normalize_word_token(token: str) -> str:
    return re.sub(r"\s+", " ", str(token or "").strip())


def extract_whisper_aligned_words_v1(
    media_path,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
    device: str = "auto",
    compute_type: str = "auto",
) -> list[dict[str, Any]]:
    """Transcribe with faster-whisper word_timestamps=True."""
    from pathlib import Path

    path = Path(media_path)
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise RuntimeError("faster-whisper not installed") from exc

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        str(path),
        beam_size=beam_size,
        vad_filter=True,
        word_timestamps=True,
        language=language,
    )
    words: list[dict[str, Any]] = []
    for seg in segments:
        for w in getattr(seg, "words", None) or []:
            token = normalize_word_token(getattr(w, "word", ""))
            start = float(getattr(w, "start", 0.0))
            end = float(getattr(w, "end", start))
            if not token or end <= start:
                continue
            words.append({"word": token, "start": round(start, 3), "end": round(end, 3)})
    if not words:
        raise RuntimeError("whisper returned no aligned words")
    return words


def _words_to_text(words: list[dict[str, Any]]) -> str:
    return " ".join(str(w.get("word") or "").strip() for w in words if str(w.get("word") or "").strip())


def _segment_from_words(
    words: list[dict[str, Any]],
    *,
    seg_idx: int,
    timing_authority: str,
) -> dict[str, Any]:
    text = _words_to_text(words)
    start = float(words[0]["start"])
    end = float(words[-1]["end"])
    return {
        "id": f"seg_{seg_idx:02d}",
        "start": format_timestamp(start),
        "end": format_timestamp(end),
        "duration_sec": round(max(0.0, end - start), 3),
        "text": text,
        "timing_authority": timing_authority,
        "token_start": 0,
        "token_end": len(words) - 1,
        "aligned_token_count": len(words),
        "start_source": timing_authority,
        "end_source": timing_authority,
    }


def chunk_aligned_words_v1(
    words: list[dict[str, Any]],
    *,
    max_chars: int = 28,
    pause_gap_sec: float = 0.4,
    min_seg_sec: float = 0.5,
    timing_authority: str = TIMING_AUTHORITY_ALIGNED,
) -> list[dict[str, Any]]:
    """Pause + max_chars chunking on aligned words; orphan text merge preserves tokens."""
    if not words:
        return []

    raw_batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal current
        if current:
            raw_batches.append(current)
            current = []

    for word in words:
        if current:
            gap = float(word["start"]) - float(current[-1]["end"])
            if gap >= pause_gap_sec:
                flush()
        candidate = current + [word]
        if len(_words_to_text(candidate)) > max_chars and current:
            flush()
            current = [word]
        else:
            current = candidate
    flush()

    merged_batches = _merge_orphan_word_batches(raw_batches)
    segments: list[dict[str, Any]] = []
    for idx, batch in enumerate(merged_batches, start=1):
        seg = _segment_from_words(batch, seg_idx=idx, timing_authority=timing_authority)
        if seg["duration_sec"] < min_seg_sec and idx < len(merged_batches):
            seg["end"] = format_timestamp(float(batch[0]["start"]) + min_seg_sec)
            seg["duration_sec"] = round(min_seg_sec, 3)
            seg["end_fallback_applied"] = True
        else:
            seg["end_fallback_applied"] = False
        segments.append(seg)
    return segments


def _merge_orphan_word_batches(batches: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    if not batches:
        return []
    texts = [_words_to_text(b) for b in batches]
    out: list[list[dict[str, Any]]] = [list(batches[0])]
    out_texts: list[str] = [texts[0]]
    i = 1
    while i < len(batches):
        text = texts[i]
        if out_texts and _is_orphan_prefix(text):
            out[-1].extend(batches[i])
            out_texts[-1] = _words_to_text(out[-1])
            i += 1
            continue
        if out_texts and _is_orphan_ending(text):
            out[-1].extend(batches[i])
            out_texts[-1] = _words_to_text(out[-1])
            i += 1
            continue
        out.append(list(batches[i]))
        out_texts.append(text)
        i += 1
    return out


def segments_from_whisper_segments_proportional_v1(
    whisper_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """P0 baseline: segment-level whisper + proportional semantic re-chunk."""
    return refine_stt_segments_semantic_ko_v1(whisper_segments)


def whisper_segments_without_words_v1(
    media_path,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
) -> list[dict[str, Any]]:
    from pathlib import Path

    path = Path(media_path)
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise RuntimeError("faster-whisper not installed") from exc

    model = WhisperModel(model_name, device="auto", compute_type="auto")
    segments, _info = model.transcribe(
        str(path),
        beam_size=beam_size,
        vad_filter=True,
        word_timestamps=False,
        language=language,
    )
    out: list[dict[str, Any]] = []
    for idx, seg in enumerate(segments, start=1):
        start = float(getattr(seg, "start", 0.0))
        end = float(getattr(seg, "end", start))
        text = str(getattr(seg, "text", "") or "").strip()
        if not text or end <= start:
            continue
        out.append(
            {
                "id": f"seg_{idx:02d}",
                "start": format_timestamp(start),
                "end": format_timestamp(end),
                "duration_sec": round(end - start, 3),
                "text": text,
            }
        )
    if not out:
        raise RuntimeError("whisper returned no segments")
    return out


def segments_proportional_from_words_v1(
    words: list[dict[str, Any]],
    *,
    min_seg_sec: float = 3.0,
) -> list[dict[str, Any]]:
    """P0 drift baseline from same transcript text, char-weighted over word span."""
    if not words:
        return []
    transcript = _words_to_text(words)
    t0 = float(words[0]["start"])
    t1 = float(words[-1]["end"])
    total = max(min_seg_sec, t1 - t0)
    segs = split_transcript_proportional_segments(transcript, total, min_seg_sec=min_seg_sec)
    for seg in segs:
        start = t0 + parse_timestamp_seconds(str(seg.get("start") or "00:00:00.00"))
        end = t0 + parse_timestamp_seconds(str(seg.get("end") or seg.get("start") or "00:00:00.00"))
        seg["start"] = format_timestamp(start)
        seg["end"] = format_timestamp(end)
        seg["duration_sec"] = round(max(0.0, end - start), 3)
        seg["timing_authority"] = TIMING_AUTHORITY_PROPORTIONAL
    return segs


def compute_timing_drift_ms_v1(
    baseline: list[dict[str, Any]],
    aligned: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mean absolute start/end drift (ms) on paired cues up to min length."""
    n = min(len(baseline), len(aligned))
    if n == 0:
        return {
            "pairs": 0,
            "start_drift_ms_mean": None,
            "end_drift_ms_mean": None,
            "start_drift_ms_max": None,
        }
    start_drifts: list[float] = []
    end_drifts: list[float] = []
    for i in range(n):
        b0 = baseline[i]
        a0 = aligned[i]
        start_drifts.append(
            abs(parse_timestamp_seconds(str(b0.get("start"))) - parse_timestamp_seconds(str(a0.get("start"))))
            * 1000.0
        )
        end_drifts.append(
            abs(parse_timestamp_seconds(str(b0.get("end"))) - parse_timestamp_seconds(str(a0.get("end")))) * 1000.0
        )
    return {
        "pairs": n,
        "start_drift_ms_mean": round(sum(start_drifts) / n, 2),
        "end_drift_ms_mean": round(sum(end_drifts) / n, 2),
        "start_drift_ms_max": round(max(start_drifts), 2),
        "end_drift_ms_max": round(max(end_drifts), 2),
    }


def format_srt_v1(segments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        start = _to_srt_ts(parse_timestamp_seconds(str(seg.get("start") or "00:00:00.00")))
        end = _to_srt_ts(parse_timestamp_seconds(str(seg.get("end") or "00:00:00.00")))
        text = str(seg.get("text") or "").strip()
        blocks.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(blocks).strip() + "\n"


def _to_srt_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_timing_spike_report_v1(
    *,
    wav_source: str,
    words: list[dict[str, Any]],
    p0_segments: list[dict[str, Any]],
    p1_segments: list[dict[str, Any]],
    stt_engine: str,
    model_name: str,
    pause_gap_sec: float,
    max_chars: int,
) -> dict[str, Any]:
    drift = compute_timing_drift_ms_v1(p0_segments, p1_segments)
    return {
        "schema": "ko_shorts_stt_timing_spike_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "wav_source": wav_source,
        "stt_engine": stt_engine,
        "model_name": model_name,
        "timing_authority_p1": TIMING_AUTHORITY_ALIGNED,
        "timing_authority_p0": TIMING_AUTHORITY_PROPORTIONAL,
        "aligned_word_count": len(words),
        "pause_gap_sec": pause_gap_sec,
        "max_chars": max_chars,
        "p0_segment_count": len(p0_segments),
        "p1_segment_count": len(p1_segments),
        "drift_vs_proportional": drift,
        "p0_segments": p0_segments,
        "p1_segments": p1_segments,
        "reproduce": "py scripts/run_ko_shorts_stt_timing_spike_v1.py --help",
    }


def transcribe_whisper_shorts_aligned_v1(
    media_path,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
    max_chars: int = 28,
    pause_gap_sec: float = 0.4,
    min_seg_sec: float = 0.5,
) -> tuple[list[dict[str, Any]], str]:
    words = extract_whisper_aligned_words_v1(
        media_path,
        model_name=model_name,
        beam_size=beam_size,
        language=language,
    )
    segments = chunk_aligned_words_v1(
        words,
        max_chars=max_chars,
        pause_gap_sec=pause_gap_sec,
        min_seg_sec=min_seg_sec,
    )
    engine = f"faster_whisper:aligned:{model_name}"
    return segments, engine
