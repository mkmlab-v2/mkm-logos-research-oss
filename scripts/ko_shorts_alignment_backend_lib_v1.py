#!/usr/bin/env python3
"""Optional alignment backends for ko shorts STT spike [HYPO]."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.ko_shorts_stt_timing_lib_v1 import (
    chunk_aligned_words_v1,
    compute_timing_drift_ms_v1,
    normalize_word_token,
    segments_proportional_from_words_v1,
    whisper_segments_without_words_v1,
)
from scripts.media_stt_transcription_lib_v1 import refine_stt_segments_semantic_ko_v1

BACKEND_FASTER_WHISPER = "faster_whisper_word_ts"
BACKEND_STABLE_TS = "stable_ts"
BACKEND_WHISPERX = "whisperx"


def extract_words_faster_whisper_v1(
    media_path: Path,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
) -> tuple[list[dict[str, Any]], str | None]:
    from scripts.ko_shorts_stt_timing_lib_v1 import extract_whisper_aligned_words_v1

    last_err: Exception | None = None
    for device, compute_type in (("auto", "auto"), ("cpu", "int8")):
        try:
            words = extract_whisper_aligned_words_v1(
                media_path,
                model_name=model_name,
                beam_size=beam_size,
                language=language,
                device=device,
                compute_type=compute_type,
            )
            return words, None
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    return [], f"{last_err.__class__.__name__}:{last_err}" if last_err else "faster_whisper_failed"


def extract_words_stable_ts_v1(
    media_path: Path,
    *,
    model_name: str = "small",
    language: str = "ko",
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        import stable_whisper  # type: ignore
    except ImportError as exc:
        return [], f"stable_ts_import_error:{exc.__class__.__name__}"
    try:
        model = stable_whisper.load_model(model_name)
        result = model.transcribe(str(media_path), language=language, word_timestamps=True)
        words: list[dict[str, Any]] = []
        for seg in result.segments or []:
            for w in getattr(seg, "words", None) or []:
                token = normalize_word_token(getattr(w, "word", ""))
                start = float(getattr(w, "start", 0.0))
                end = float(getattr(w, "end", start))
                if not token or end <= start:
                    continue
                words.append({"word": token, "start": round(start, 3), "end": round(end, 3)})
        if not words:
            return [], "stable_ts_no_words"
        return words, None
    except Exception as exc:  # noqa: BLE001
        return [], f"stable_ts_error:{exc.__class__.__name__}:{exc}"


def extract_words_whisperx_v1(
    media_path: Path,
    *,
    model_name: str = "small",
    language: str = "ko",
    device: str = "cpu",
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        import whisperx  # type: ignore
    except ImportError as exc:
        return [], f"whisperx_import_error:{exc.__class__.__name__}"
    try:
        audio = whisperx.load_audio(str(media_path))
        model = whisperx.load_model(model_name, device=device, compute_type="int8")
        result = model.transcribe(audio, language=language)
        model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
        aligned = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
        words: list[dict[str, Any]] = []
        for seg in aligned.get("segments") or []:
            for w in seg.get("words") or []:
                token = normalize_word_token(str(w.get("word") or ""))
                start = float(w.get("start") or 0.0)
                end = float(w.get("end") or start)
                if not token or end <= start:
                    continue
                words.append({"word": token, "start": round(start, 3), "end": round(end, 3)})
        if not words:
            return [], "whisperx_no_words"
        return words, None
    except Exception as exc:  # noqa: BLE001
        return [], f"whisperx_error:{exc.__class__.__name__}:{exc}"


def extract_words_for_backend_v1(
    backend: str,
    media_path: Path,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
) -> tuple[list[dict[str, Any]], str | None]:
    if backend == BACKEND_FASTER_WHISPER:
        return extract_words_faster_whisper_v1(
            media_path, model_name=model_name, beam_size=beam_size, language=language
        )
    if backend == BACKEND_STABLE_TS:
        return extract_words_stable_ts_v1(media_path, model_name=model_name, language=language)
    if backend == BACKEND_WHISPERX:
        return extract_words_whisperx_v1(media_path, model_name=model_name, language=language)
    raise ValueError(f"unknown backend: {backend}")


def word_timing_stats_v1(words: list[dict[str, Any]]) -> dict[str, Any]:
    if len(words) < 2:
        return {"word_count": len(words), "max_inter_word_gap_ms": None, "mean_word_dur_ms": None}
    gaps = []
    durs = []
    for i, w in enumerate(words):
        durs.append((float(w["end"]) - float(w["start"])) * 1000.0)
        if i > 0:
            gaps.append((float(w["start"]) - float(words[i - 1]["end"])) * 1000.0)
    return {
        "word_count": len(words),
        "max_inter_word_gap_ms": round(max(gaps), 2) if gaps else None,
        "mean_word_dur_ms": round(sum(durs) / len(durs), 2) if durs else None,
    }


def benchmark_alignment_backend_v1(
    media_path: Path,
    backend: str,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
    max_chars: int = 28,
    pause_gap_sec: float = 0.4,
    min_seg_sec: float = 0.5,
    p0_whisper_semantic: bool = False,
) -> dict[str, Any]:
    words, err = extract_words_for_backend_v1(
        backend,
        media_path,
        model_name=model_name,
        beam_size=beam_size,
        language=language,
    )
    entry: dict[str, Any] = {
        "backend": backend,
        "ok": err is None,
        "error": err,
        "word_stats": word_timing_stats_v1(words) if words else {},
    }
    if err or not words:
        return entry
    p1 = chunk_aligned_words_v1(
        words,
        max_chars=max_chars,
        pause_gap_sec=pause_gap_sec,
        min_seg_sec=min_seg_sec,
    )
    p0 = segments_proportional_from_words_v1(words, min_seg_sec=min_seg_sec)
    if p0_whisper_semantic and backend == BACKEND_FASTER_WHISPER:
        try:
            whisper_segs = whisper_segments_without_words_v1(
                media_path,
                model_name=model_name,
                beam_size=beam_size,
                language=language,
            )
            p0 = refine_stt_segments_semantic_ko_v1(whisper_segs)
        except Exception:
            pass
    drift = compute_timing_drift_ms_v1(p0, p1)
    entry.update(
        {
            "p1_segment_count": len(p1),
            "p0_segment_count": len(p0),
            "drift_vs_proportional": drift,
            "sample_p1_texts": [str(s.get("text") or "")[:40] for s in p1[:3]],
        }
    )
    return entry
