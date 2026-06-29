#!/usr/bin/env python3
"""Korean shorts segment backends — semantic_chunk vs KSS vs optional KSSDS [HYPO]."""

from __future__ import annotations

from typing import Any

from scripts.media_stt_transcription_lib_v1 import (
    _merge_orphan_endings,
    _merge_orphan_prefixes,
    _split_long_eojeol,
    semantic_chunk_ko_v1,
)

BACKEND_SEMANTIC = "semantic_chunk_ko_v1"
BACKEND_KSS_FAST = "kss_fast"
BACKEND_KSSDS = "kssds"

NETFLIX_MAX_CHARS = 16
SHORTS_DEFAULT_MAX_CHARS = 28
NETFLIX_CPS_TARGET = 12.0


def apply_shorts_line_cap_v1(lines: list[str], *, max_chars: int = SHORTS_DEFAULT_MAX_CHARS) -> list[str]:
    """Split long lines by eojeol for subtitle CPL without full semantic re-chunk."""
    out: list[str] = []
    for line in lines:
        text = " ".join(str(line or "").split())
        if not text:
            continue
        if len(text) <= max_chars:
            out.append(text)
        else:
            out.extend(_split_long_eojeol(text, max_chars))
    merged = _merge_orphan_prefixes(out, max_chars=max_chars)
    final = _merge_orphan_endings(merged, max_chars=max_chars)
    return [c.strip() for c in final if c.strip()]


def segment_semantic_chunk_ko_v1(text: str, *, max_chars: int = SHORTS_DEFAULT_MAX_CHARS) -> list[str]:
    return semantic_chunk_ko_v1(text, max_chars=max_chars)


def segment_kss_fast_ko_v1(text: str, *, max_chars: int = SHORTS_DEFAULT_MAX_CHARS) -> list[str]:
    import kss

    normalized = " ".join(str(text or "").split())
    if not normalized:
        return []
    sentences = kss.split_sentences(normalized, backend="fast")
    return apply_shorts_line_cap_v1([str(s).strip() for s in sentences if str(s).strip()], max_chars=max_chars)


def segment_kssds_ko_v1(text: str, *, max_chars: int = SHORTS_DEFAULT_MAX_CHARS) -> tuple[list[str] | None, str | None]:
    """Optional KSSDS backend; returns (lines, error) — error set when unavailable."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return [], None
    try:
        from KSSDS import KSSDS  # type: ignore
    except ImportError as exc:
        return None, f"kssds_import_error:{exc.__class__.__name__}"
    except Exception as exc:  # noqa: BLE001 — surface HF/transformers drift
        return None, f"kssds_init_error:{exc.__class__.__name__}:{exc}"
    try:
        splitter = KSSDS()
        sentences = splitter.split_sentences(normalized)
    except Exception as exc:  # noqa: BLE001
        return None, f"kssds_split_error:{exc.__class__.__name__}:{exc}"
    lines = apply_shorts_line_cap_v1([str(s).strip() for s in sentences if str(s).strip()], max_chars=max_chars)
    return lines, None


def split_text_for_shorts_v1(
    text: str,
    backend: str,
    *,
    max_chars: int = SHORTS_DEFAULT_MAX_CHARS,
) -> tuple[list[str], str | None]:
    """Return (lines, backend_error). backend_error is None on success."""
    if backend == BACKEND_SEMANTIC:
        return segment_semantic_chunk_ko_v1(text, max_chars=max_chars), None
    if backend == BACKEND_KSS_FAST:
        return segment_kss_fast_ko_v1(text, max_chars=max_chars), None
    if backend == BACKEND_KSSDS:
        lines, err = segment_kssds_ko_v1(text, max_chars=max_chars)
        return (lines or []), err
    raise ValueError(f"unknown backend: {backend}")


def compute_subtitle_line_metrics_v1(
    lines: list[str],
    *,
    duration_sec: float | None = None,
    netflix_max_chars: int = NETFLIX_MAX_CHARS,
    shorts_max_chars: int = SHORTS_DEFAULT_MAX_CHARS,
) -> dict[str, Any]:
    clean = [str(x).strip() for x in lines if str(x).strip()]
    char_lens = [len(x) for x in clean]
    line_count = len(clean)
    total_chars = sum(char_lens)
    metrics: dict[str, Any] = {
        "line_count": line_count,
        "total_chars": total_chars,
        "max_line_chars": max(char_lens) if char_lens else 0,
        "mean_line_chars": round(total_chars / line_count, 2) if line_count else 0.0,
        "lines_over_shorts_max": sum(1 for n in char_lens if n > shorts_max_chars),
        "lines_over_netflix_max": sum(1 for n in char_lens if n > netflix_max_chars),
        "shorts_max_chars": shorts_max_chars,
        "netflix_max_chars": netflix_max_chars,
    }
    if duration_sec and duration_sec > 0 and line_count > 0:
        metrics["duration_sec"] = round(float(duration_sec), 3)
        metrics["cps_mean"] = round(total_chars / float(duration_sec), 2)
        metrics["cps_per_line_mean"] = round(
            sum(n / (float(duration_sec) / line_count) for n in char_lens) / line_count, 2
        )
        metrics["netflix_cps_over_12"] = metrics["cps_mean"] > NETFLIX_CPS_TARGET
    return metrics


def compare_backends_on_text_v1(
    text: str,
    *,
    duration_sec: float | None = None,
    max_chars: int = SHORTS_DEFAULT_MAX_CHARS,
    backends: tuple[str, ...] = (BACKEND_SEMANTIC, BACKEND_KSS_FAST, BACKEND_KSSDS),
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for backend in backends:
        lines, err = split_text_for_shorts_v1(text, backend, max_chars=max_chars)
        entry: dict[str, Any] = {
            "backend": backend,
            "ok": err is None,
            "error": err,
            "lines": lines if err is None else [],
            "metrics": compute_subtitle_line_metrics_v1(lines or [], duration_sec=duration_sec, shorts_max_chars=max_chars),
        }
        results[backend] = entry
    return results
