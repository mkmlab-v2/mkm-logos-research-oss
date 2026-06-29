#!/usr/bin/env python3
"""STT engine helpers for media_stt_transcription_v1 [HYPO]."""

from __future__ import annotations

import re
import wave
from pathlib import Path
from typing import Any

# Korean subtitle semantic chunking (4-step: punct → eojeol → prefix merge → ending merge)
_SENT_BOUNDARY_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
_ORPHAN_ENDING_RE = re.compile(
    r"^(습니다|합니다|줍니다|입니다|됩니다|있습니다|없습니다|"
    r"해요|돼요|이에요|예요|네요|거예요|것입니다|문화입니다|다)\.?$"
)
_ORPHAN_ENDING_TAIL_RE = re.compile(r"(니다|습니다|해요|돼요|입니다|예요|것입니다|문화입니다)\.?$")
_ENUM_PREFIX_RE = re.compile(r"^(첫째|둘째|셋째|넷째|다섯째|하나|둘|셋)[,，]?")


def format_timestamp(seconds: float) -> str:
    sec = max(0.0, float(seconds))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def wav_duration_sec(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.getnframes()
        if rate <= 0:
            return 0.0
        return frames / float(rate)


def parse_timestamp_seconds(ts: str) -> float:
    m = re.match(r"(\d{2}):(\d{2}):(\d{2}\.?\d*)", str(ts).strip())
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _split_punctuation_boundaries(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_BOUNDARY_RE.split(text.strip()) if p.strip()]
    return parts if parts else ([text.strip()] if text.strip() else [])


def _split_long_eojeol(part: str, max_chars: int) -> list[str]:
    if len(part) <= max_chars:
        return [part]
    words = part.split()
    if not words:
        return [part]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += extra
    if current:
        chunks.append(" ".join(current))
    return chunks


def _is_orphan_prefix(chunk: str) -> bool:
    s = chunk.strip()
    if not s:
        return False
    if s.endswith((",", "，", "·")):
        return len(s) <= 12
    m = _ENUM_PREFIX_RE.match(s)
    if not m:
        return False
    rest = s[m.end() :].strip()
    return not rest and len(s) <= 8


def _is_orphan_ending(chunk: str) -> bool:
    s = chunk.strip()
    if not s:
        return False
    if _ORPHAN_ENDING_RE.match(s):
        return True
    if " " in s:
        return False
    return len(s) <= 8 and bool(_ORPHAN_ENDING_TAIL_RE.search(s))


def _merge_orphan_prefixes(chunks: list[str], *, max_chars: int | None = None) -> list[str]:
    if not chunks:
        return []
    out: list[str] = []
    i = 0
    while i < len(chunks):
        cur = chunks[i]
        while i + 1 < len(chunks) and _is_orphan_prefix(cur):
            merged = f"{cur} {chunks[i + 1]}".strip()
            if max_chars is not None and len(merged) > max_chars:
                break
            i += 1
            cur = merged
        out.append(cur)
        i += 1
    return out


def _merge_orphan_endings(chunks: list[str], *, max_chars: int | None = None) -> list[str]:
    out: list[str] = []
    for chunk in chunks:
        if out and _is_orphan_ending(chunk):
            merged = f"{out[-1]} {chunk}".strip()
            if max_chars is None or len(merged) <= max_chars:
                out[-1] = merged
            else:
                out.append(chunk)
        else:
            out.append(chunk)
    return out


def rebalance_orphan_ending_cues_v1(lines: list[str], *, max_chars: int) -> list[str]:
    """Move trailing eojeol from previous line to absorb orphan ending under CPL."""
    out = [c.strip() for c in lines if str(c or "").strip()]
    if len(out) < 2 or not _is_orphan_ending(out[-1]):
        return out
    prev, ending = out[-2], out[-1]
    parts = prev.split()
    if len(parts) < 2:
        return out
    moved = parts[-1]
    new_prev = " ".join(parts[:-1]).strip()
    new_cur = f"{moved} {ending}".strip()
    if new_prev and len(new_prev) <= max_chars and len(new_cur) <= max_chars:
        out[-2] = new_prev
        out[-1] = new_cur
    return out


def rebalance_orphan_prefix_cues_v1(lines: list[str], *, max_chars: int) -> list[str]:
    out = [c.strip() for c in lines if str(c or "").strip()]
    if len(out) < 2:
        return out
    for i in range(len(out) - 1):
        if not _is_orphan_prefix(out[i]):
            continue
        cur, nxt = out[i], out[i + 1]
        if cur.endswith((",", "，", "·")):
            merged = f"{cur} {nxt}".strip()
            if len(merged) <= max_chars:
                out[i : i + 2] = [merged]
            else:
                parts = nxt.split()
                if parts:
                    moved = parts[0]
                    new_cur = f"{cur} {moved}".strip()
                    new_nxt = " ".join(parts[1:]).strip()
                    if len(new_cur) <= max_chars and (not new_nxt or len(new_nxt) <= max_chars):
                        repl = [new_cur]
                        if new_nxt:
                            repl.append(new_nxt)
                        out[i : i + 2] = repl
            break
    return out


def coalesce_orphan_chunks_v1(lines: list[str], *, max_chars: int) -> list[str]:
    """Re-merge orphan prefix/ending fragments; re-chunk when simple merge exceeds CPL."""
    work = [c.strip() for c in lines if str(c or "").strip()]
    if not work:
        return []
    work = _merge_orphan_prefixes(work, max_chars=max_chars)
    work = _merge_orphan_endings(work, max_chars=max_chars)
    out: list[str] = []
    i = 0
    while i < len(work):
        cur = work[i]
        if i + 1 < len(work) and _is_orphan_prefix(cur):
            combined = f"{cur} {work[i + 1]}".strip()
            out.extend(semantic_chunk_ko_v1(combined, max_chars=max_chars))
            i += 2
            continue
        if out and _is_orphan_ending(cur):
            combined = f"{out[-1]} {cur}".strip()
            out.pop()
            out.extend(semantic_chunk_ko_v1(combined, max_chars=max_chars))
            i += 1
            continue
        out.append(cur)
        i += 1
    merged = _merge_orphan_prefixes(out, max_chars=max_chars)
    final = _merge_orphan_endings(merged, max_chars=max_chars)
    final = rebalance_orphan_prefix_cues_v1(final, max_chars=max_chars)
    final = rebalance_orphan_ending_cues_v1(final, max_chars=max_chars)
    return [c for c in final if c]


def semantic_chunk_ko_v1(text: str, *, max_chars: int = 28) -> list[str]:
    """Meaning-complete Korean subtitle lines for STT post-process [HYPO]."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return []
    parts = _split_punctuation_boundaries(normalized)
    expanded: list[str] = []
    for part in parts:
        expanded.extend(_split_long_eojeol(part, max_chars))
    merged = _merge_orphan_prefixes(expanded, max_chars=max_chars)
    final = _merge_orphan_endings(merged, max_chars=max_chars)
    return [c.strip() for c in final if c.strip()]


def refine_stt_segments_semantic_ko_v1(
    segments: list[dict[str, Any]],
    *,
    max_chars: int = 28,
    min_seg_sec: float = 0.5,
) -> list[dict[str, Any]]:
    """Re-chunk STT segments with semantic_chunk_ko_v1 and proportional timestamps."""
    if not segments:
        return []
    joined = " ".join(str(s.get("text") or "").strip() for s in segments if str(s.get("text") or "").strip())
    chunks = semantic_chunk_ko_v1(joined, max_chars=max_chars)
    if not chunks:
        return segments

    starts = [parse_timestamp_seconds(str(s.get("start") or "00:00:00.00")) for s in segments]
    ends = [
        parse_timestamp_seconds(str(s.get("end") or s.get("start") or "00:00:00.00")) for s in segments
    ]
    t0 = starts[0] if starts else 0.0
    t1 = max(ends) if ends else t0 + 1.0
    total = max(min_seg_sec, t1 - t0)

    weights = [max(1, len(c)) for c in chunks]
    total_w = float(sum(weights))
    cursor = t0
    out: list[dict[str, Any]] = []
    for idx, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        start = cursor
        if idx == len(chunks):
            end = t0 + total
        else:
            seg_dur = max(min_seg_sec, total * (weight / total_w))
            end = min(t0 + total, cursor + seg_dur)
        if end <= start:
            end = min(t0 + total, start + min_seg_sec)
        out.append(
            {
                "id": f"seg_{idx:02d}",
                "start": format_timestamp(start),
                "end": format_timestamp(end),
                "duration_sec": round(max(0.0, end - start), 3),
                "text": chunk,
            }
        )
        cursor = end
    return out


def split_transcript_proportional_segments(
    transcript: str,
    total_sec: float,
    *,
    min_seg_sec: float = 3.0,
) -> list[dict[str, Any]]:
    """Approximate segment timestamps when STT returns text-only [HYPO]."""
    text = transcript.strip()
    if not text:
        return []
    parts = semantic_chunk_ko_v1(text)
    if not parts:
        parts = [text]
    weights = [max(1, len(p)) for p in parts]
    total_w = float(sum(weights))
    cursor = 0.0
    segments: list[dict[str, Any]] = []
    for idx, (part, weight) in enumerate(zip(parts, weights), start=1):
        start = cursor
        if idx == len(parts):
            end = total_sec
        else:
            seg_dur = max(min_seg_sec, total_sec * (weight / total_w))
            end = min(total_sec, cursor + seg_dur)
        if end <= start:
            end = min(total_sec, start + min_seg_sec)
        segments.append(
            {
                "id": f"seg_{idx:02d}",
                "start": format_timestamp(start),
                "end": format_timestamp(end),
                "duration_sec": round(max(0.0, end - start), 3),
                "text": part,
            }
        )
        cursor = end
    return segments


def transcribe_whisper_segments(
    media_path: Path,
    *,
    model_name: str = "small",
    beam_size: int = 5,
    language: str = "ko",
    timing_mode: str = "proportional",
) -> list[dict[str, Any]]:
    mode = str(timing_mode or "proportional").strip().lower()
    if mode == "aligned":
        from scripts.ko_shorts_stt_timing_lib_v1 import transcribe_whisper_shorts_aligned_v1

        segments, _engine = transcribe_whisper_shorts_aligned_v1(
            media_path,
            model_name=model_name,
            beam_size=beam_size,
            language=language,
        )
        return segments

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise RuntimeError("faster-whisper not installed") from exc

    model = WhisperModel(model_name, device="auto", compute_type="auto")
    segments, _info = model.transcribe(
        str(media_path),
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
    return refine_stt_segments_semantic_ko_v1(out)


def transcribe_sherpa_segments(wav_path: Path) -> list[dict[str, Any]]:
    from scripts.smoke_sherpa_onnx_stt_btrack_v1 import _transcribe_local

    tx = _transcribe_local(wav_path)
    transcript = str(tx.get("transcript") or "").strip()
    if not transcript:
        raise RuntimeError("sherpa returned empty transcript")
    total = wav_duration_sec(wav_path)
    segs = split_transcript_proportional_segments(transcript, total)
    if not segs:
        segs = [
            {
                "id": "seg_01",
                "start": "00:00:00.00",
                "end": format_timestamp(total),
                "duration_sec": round(total, 3),
                "text": transcript,
            }
        ]
    return segs


def resolve_stt_segments(
    wav_path: Path,
    *,
    engine: str,
    model_name: str = "small",
    beam_size: int = 5,
    timing_mode: str = "proportional",
) -> tuple[list[dict[str, Any]], str]:
    eng = engine.strip().lower()
    mode = str(timing_mode or "proportional").strip().lower()
    if eng == "whisper":
        segments = transcribe_whisper_segments(
            wav_path,
            model_name=model_name,
            beam_size=beam_size,
            timing_mode=mode,
        )
        if mode == "aligned":
            return segments, f"faster_whisper:aligned:{model_name}"
        return segments, f"faster_whisper:{model_name}"
    if eng == "sherpa":
        return transcribe_sherpa_segments(wav_path), "sherpa_onnx:sense_voice"
    if eng == "auto":
        try:
            segments = transcribe_whisper_segments(
                wav_path,
                model_name=model_name,
                beam_size=beam_size,
                timing_mode=mode,
            )
            if mode == "aligned":
                return segments, f"faster_whisper:aligned:{model_name}"
            return segments, f"faster_whisper:{model_name}"
        except RuntimeError:
            return transcribe_sherpa_segments(wav_path), "sherpa_onnx:sense_voice"
    raise ValueError(f"unknown engine: {engine}")
