#!/usr/bin/env python3
"""Subtitle profile gates — Netflix 16 CPL / 12 CPS vs shorts 28 [HYPO]."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.ko_shorts_segment_backend_lib_v1 import (
    BACKEND_SEMANTIC,
    NETFLIX_CPS_TARGET,
    NETFLIX_MAX_CHARS,
    SHORTS_DEFAULT_MAX_CHARS,
    apply_shorts_line_cap_v1,
    compute_subtitle_line_metrics_v1,
    split_text_for_shorts_v1,
)
from scripts.media_stt_transcription_lib_v1 import (
    _is_orphan_ending,
    _is_orphan_prefix,
    coalesce_orphan_chunks_v1,
    format_timestamp,
    parse_timestamp_seconds,
    refine_stt_segments_semantic_ko_v1,
    semantic_chunk_ko_v1,
)

PROFILE_SHORTS_V28 = "shorts_v28"
PROFILE_NETFLIX_V16 = "netflix_v16"
PROFILE_NETFLIX_V16_PRO = "netflix_v16_pro"


@dataclass(frozen=True)
class SubtitleProfileV1:
    key: str
    max_chars: int
    netflix_max_chars: int
    cps_target: float
    cps_hard_max: float
    label: str


PROFILES: dict[str, SubtitleProfileV1] = {
    PROFILE_SHORTS_V28: SubtitleProfileV1(
        key=PROFILE_SHORTS_V28,
        max_chars=SHORTS_DEFAULT_MAX_CHARS,
        netflix_max_chars=NETFLIX_MAX_CHARS,
        cps_target=NETFLIX_CPS_TARGET,
        cps_hard_max=17.0,
        label="MKM shorts draft (28 chars)",
    ),
    PROFILE_NETFLIX_V16: SubtitleProfileV1(
        key=PROFILE_NETFLIX_V16,
        max_chars=NETFLIX_MAX_CHARS,
        netflix_max_chars=NETFLIX_MAX_CHARS,
        cps_target=NETFLIX_CPS_TARGET,
        cps_hard_max=17.0,
        label="Netflix Korean TTSG proxy (16 chars / 12 CPS)",
    ),
    PROFILE_NETFLIX_V16_PRO: SubtitleProfileV1(
        key=PROFILE_NETFLIX_V16_PRO,
        max_chars=NETFLIX_MAX_CHARS,
        netflix_max_chars=NETFLIX_MAX_CHARS,
        cps_target=NETFLIX_CPS_TARGET,
        cps_hard_max=17.0,
        label="Netflix Korean TTSG proxy + pro ASS typography (16 CPL)",
    ),
}


def segments_text_duration_span(segments: list[dict[str, Any]]) -> float:
    if not segments:
        return 0.0
    starts = [parse_timestamp_seconds(str(s.get("start") or "00:00:00.00")) for s in segments]
    ends = [
        parse_timestamp_seconds(str(s.get("end") or s.get("start") or "00:00:00.00")) for s in segments
    ]
    return max(0.0, max(ends) - min(starts))


def two_pass_chunk_text_v1(text: str, *, max_chars: int) -> list[str]:
    """Pass1 semantic orphan-aware; pass2 hard CPL cap on each cue."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return []
    semantic = semantic_chunk_ko_v1(normalized, max_chars=max_chars)
    hard: list[str] = []
    for line in semantic:
        if len(line) <= max_chars:
            hard.append(line)
        else:
            hard.extend(apply_shorts_line_cap_v1([line], max_chars=max_chars))
    return coalesce_orphan_chunks_v1(hard, max_chars=max_chars)


def _subdivide_parent_segment_v1(
    parent: dict[str, Any],
    lines: list[str],
    *,
    profile: SubtitleProfileV1,
    seg_idx_start: int,
    min_cue_sec: float = 0.35,
) -> list[dict[str, Any]]:
    if not lines:
        return []
    t0 = parse_timestamp_seconds(str(parent.get("start") or "00:00:00.00"))
    t1 = parse_timestamp_seconds(str(parent.get("end") or parent.get("start") or "00:00:00.00"))
    span = max(min_cue_sec * len(lines), t1 - t0)
    weights = [max(1, len(c)) for c in lines]
    total_w = float(sum(weights))
    cursor = t0
    out: list[dict[str, Any]] = []
    for offset, (line, weight) in enumerate(zip(lines, weights)):
        start = cursor
        if offset == len(lines) - 1:
            end = t0 + span
        else:
            dur = max(min_cue_sec, span * (weight / total_w))
            min_cps_dur = len(line) / profile.cps_hard_max if profile.cps_hard_max > 0 else min_cue_sec
            dur = max(dur, min_cps_dur)
            end = min(t0 + span, cursor + dur)
        if end <= start:
            end = min(t0 + span, start + min_cue_sec)
        out.append(
            {
                "id": f"seg_{seg_idx_start + offset:02d}",
                "start": format_timestamp(start),
                "end": format_timestamp(end),
                "duration_sec": round(max(0.0, end - start), 3),
                "text": line,
                "profile": profile.key,
                "refine_mode": "two_pass_per_parent",
                "parent_id": parent.get("id"),
            }
        )
        cursor = end
    return out


def refine_segments_two_pass_v1(
    segments: list[dict[str, Any]],
    profile: SubtitleProfileV1,
    *,
    min_cue_sec: float = 0.35,
) -> list[dict[str, Any]]:
    """Recommended: keep P1 parent timing; two-pass chunk inside each parent cue."""
    out: list[dict[str, Any]] = []
    idx = 1
    for parent in segments:
        text = str(parent.get("text") or "").strip()
        if not text:
            continue
        lines = two_pass_chunk_text_v1(text, max_chars=profile.max_chars)
        if not lines:
            continue
        if len(lines) == 1 and len(lines[0]) <= profile.max_chars:
            out.append(
                {
                    **parent,
                    "id": f"seg_{idx:02d}",
                    "text": lines[0],
                    "profile": profile.key,
                    "refine_mode": "two_pass_per_parent",
                }
            )
            idx += 1
            continue
        subdivided = _subdivide_parent_segment_v1(
            parent,
            lines,
            profile=profile,
            seg_idx_start=idx,
            min_cue_sec=min_cue_sec,
        )
        out.extend(subdivided)
        idx += len(subdivided)
    return _merge_adjacent_orphan_segment_cues_v1(out, profile)


def _merge_adjacent_orphan_segment_cues_v1(
    segments: list[dict[str, Any]],
    profile: SubtitleProfileV1,
) -> list[dict[str, Any]]:
    """Merge cross-cue orphan prefix/ending fragments when CPL allows."""
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(segments):
        cur = dict(segments[i])
        text = str(cur.get("text") or "").strip()
        if i + 1 < len(segments) and _is_orphan_prefix(text):
            nxt = segments[i + 1]
            nxt_text = str(nxt.get("text") or "").strip()
            merged = f"{text} {nxt_text}".strip()
            if len(merged) <= profile.max_chars:
                cur["text"] = merged
                cur["end"] = nxt.get("end")
                end_sec = parse_timestamp_seconds(str(cur.get("end") or cur.get("start") or "00:00:00.00"))
                start_sec = parse_timestamp_seconds(str(cur.get("start") or "00:00:00.00"))
                cur["duration_sec"] = round(max(0.0, end_sec - start_sec), 3)
                out.append(cur)
                i += 2
                continue
            combined_parent = {
                "id": cur.get("id"),
                "start": cur.get("start"),
                "end": nxt.get("end"),
            }
            lines = two_pass_chunk_text_v1(f"{text} {nxt_text}".strip(), max_chars=profile.max_chars)
            if lines and not any(_is_orphan_prefix(x) or _is_orphan_ending(x) for x in lines):
                subdivided = _subdivide_parent_segment_v1(
                    combined_parent,
                    lines,
                    profile=profile,
                    seg_idx_start=len(out) + 1,
                )
                out.extend(subdivided)
                i += 2
                continue
        if out and _is_orphan_ending(text):
            prev = out[-1]
            merged = f"{str(prev.get('text') or '').strip()} {text}".strip()
            if len(merged) <= profile.max_chars:
                prev["text"] = merged
                prev["end"] = cur.get("end")
                end_sec = parse_timestamp_seconds(str(prev.get("end") or prev.get("start") or "00:00:00.00"))
                start_sec = parse_timestamp_seconds(str(prev.get("start") or "00:00:00.00"))
                prev["duration_sec"] = round(max(0.0, end_sec - start_sec), 3)
                i += 1
                continue
        if out and _is_orphan_prefix(text) and i + 1 >= len(segments):
            prev = out[-1]
            merged = f"{str(prev.get('text') or '').strip()} {text}".strip()
            if len(merged) <= profile.max_chars:
                prev["text"] = merged
                prev["end"] = cur.get("end")
                end_sec = parse_timestamp_seconds(str(prev.get("end") or prev.get("start") or "00:00:00.00"))
                start_sec = parse_timestamp_seconds(str(prev.get("start") or "00:00:00.00"))
                prev["duration_sec"] = round(max(0.0, end_sec - start_sec), 3)
                i += 1
                continue
        out.append(cur)
        i += 1
    return out


def refine_segments_for_profile_v1(
    segments: list[dict[str, Any]],
    profile: SubtitleProfileV1,
    *,
    backend: str = BACKEND_SEMANTIC,
    two_pass: bool = True,
) -> list[dict[str, Any]]:
    """Re-chunk segment texts to profile max_chars; preserve span with proportional timing."""
    if not segments:
        return []
    if two_pass:
        return refine_segments_two_pass_v1(segments, profile)
    joined = " ".join(str(s.get("text") or "").strip() for s in segments if str(s.get("text") or "").strip())
    lines, err = split_text_for_shorts_v1(joined, backend, max_chars=profile.max_chars)
    if err or not lines:
        return refine_stt_segments_semantic_ko_v1(segments, max_chars=profile.max_chars)

    t0 = parse_timestamp_seconds(str(segments[0].get("start") or "00:00:00.00"))
    t1 = parse_timestamp_seconds(
        str(segments[-1].get("end") or segments[-1].get("start") or "00:00:00.00")
    )
    total = max(0.5, t1 - t0)
    weights = [max(1, len(c)) for c in lines]
    total_w = float(sum(weights))
    cursor = t0
    out: list[dict[str, Any]] = []
    for idx, (line, weight) in enumerate(zip(lines, weights), start=1):
        start = cursor
        if idx == len(lines):
            end = t0 + total
        else:
            seg_dur = max(0.5, total * (weight / total_w))
            end = min(t0 + total, cursor + seg_dur)
        if end <= start:
            end = min(t0 + total, start + 0.5)
        out.append(
            {
                "id": f"seg_{idx:02d}",
                "start": format_timestamp(start),
                "end": format_timestamp(end),
                "duration_sec": round(max(0.0, end - start), 3),
                "text": line,
                "profile": profile.key,
            }
        )
        cursor = end
    return out


def compute_cue_cps_v1(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text") or "").strip()
        start = parse_timestamp_seconds(str(seg.get("start") or "00:00:00.00"))
        end = parse_timestamp_seconds(str(seg.get("end") or "00:00:00.00"))
        dur = max(0.001, end - start)
        chars = len(text)
        cues.append(
            {
                "id": seg.get("id"),
                "text": text,
                "chars": chars,
                "duration_sec": round(dur, 3),
                "cps": round(chars / dur, 2),
            }
        )
    return cues


def evaluate_subtitle_gate_v1(
    segments: list[dict[str, Any]],
    profile: SubtitleProfileV1,
) -> dict[str, Any]:
    lines = [str(s.get("text") or "").strip() for s in segments if str(s.get("text") or "").strip()]
    span = segments_text_duration_span(segments)
    line_metrics = compute_subtitle_line_metrics_v1(
        lines,
        duration_sec=span if span > 0 else None,
        netflix_max_chars=profile.netflix_max_chars,
        shorts_max_chars=profile.max_chars,
    )
    cue_cps = compute_cue_cps_v1(segments)
    over_char = [c for c in cue_cps if c["chars"] > profile.max_chars]
    over_cps = [c for c in cue_cps if c["cps"] > profile.cps_hard_max]
    over_cps_target = [c for c in cue_cps if c["cps"] > profile.cps_target]
    char_ok = len(over_char) == 0
    cps_ok = len(over_cps) == 0
    cps_target_ok = len(over_cps_target) == 0
    gate_pass = char_ok and cps_ok
    return {
        "profile": profile.key,
        "profile_label": profile.label,
        "gate_pass": gate_pass,
        "char_gate_pass": char_ok,
        "cps_hard_gate_pass": cps_ok,
        "cps_target_pass": cps_target_ok,
        "cue_count": len(cue_cps),
        "line_metrics": line_metrics,
        "over_max_chars_cues": over_char,
        "over_cps_hard_cues": over_cps,
        "over_cps_target_cues": over_cps_target,
        "max_cps": max((c["cps"] for c in cue_cps), default=0.0),
        "mean_cps": round(sum(c["cps"] for c in cue_cps) / len(cue_cps), 2) if cue_cps else 0.0,
    }
