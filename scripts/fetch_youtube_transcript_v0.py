#!/usr/bin/env python3
"""Fetch YouTube captions and format for media ingest parser [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")
_URL_PATTERNS = (
    re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)(?P<id>[\w-]{11})"),
    re.compile(r"youtube\.com/shorts/(?P<id>[\w-]{11})"),
)


def extract_youtube_video_id(url_or_id: str) -> str | None:
    raw = str(url_or_id or "").strip()
    if not raw:
        return None
    if _VIDEO_ID_RE.match(raw):
        return raw
    for pat in _URL_PATTERNS:
        m = pat.search(raw)
        if m:
            return m.group("id")
    return None


def format_transcript_snippets(snippets: list[dict[str, Any]]) -> str:
    """Convert API snippets to plain MM:SS blocks for parse_youtube_transcript_segments_v0."""
    lines: list[str] = []
    for row in snippets:
        text = re.sub(r"\s+", " ", str(row.get("text") or "")).strip()
        if not text:
            continue
        start = float(row.get("start") or 0.0)
        total_sec = int(start)
        minutes, seconds = divmod(total_sec, 60)
        lines.append(f"{minutes}:{seconds:02d}{text}")
    return "\n".join(lines)


def _normalize_snippets(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in raw:
        if isinstance(row, dict):
            out.append(row)
            continue
        text = getattr(row, "text", None)
        start = getattr(row, "start", None)
        if text is None:
            continue
        out.append(
            {
                "text": str(text),
                "start": float(start or 0.0),
                "duration": float(getattr(row, "duration", 0.0) or 0.0),
            }
        )
    return out


def _fetch_transcript_snippets(
    video_id: str,
    languages: tuple[str, ...],
) -> tuple[list[dict[str, Any]] | None, str | None, list[str]]:
    from youtube_transcript_api import YouTubeTranscriptApi

    errors: list[str] = []
    api = YouTubeTranscriptApi()

    if hasattr(api, "fetch"):
        for lang in languages:
            try:
                fetched = api.fetch(video_id, languages=[lang])
                return _normalize_snippets(fetched), lang, errors
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{lang}: {exc}")
        try:
            fetched = api.fetch(video_id)
            return _normalize_snippets(fetched), None, errors
        except Exception as exc:  # noqa: BLE001
            errors.append(f"default: {exc}")
            return None, None, errors

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        for lang in languages:
            try:
                snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                return _normalize_snippets(snippets), lang, errors
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{lang}: {exc}")

    return None, None, errors


def fetch_youtube_transcript_v0(
    url_or_id: str,
    *,
    languages: tuple[str, ...] = ("ko", "en"),
    dry_run: bool = False,
) -> dict[str, Any]:
    video_id = extract_youtube_video_id(url_or_id)
    if not video_id:
        return {"ok": False, "error": "invalid_video_id", "input": url_or_id}

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "video_id": video_id,
            "languages": list(languages),
        }

    try:
        snippets, picked_lang, errors = _fetch_transcript_snippets(video_id, languages)
    except ImportError:
        return {
            "ok": False,
            "error": "missing_dependency",
            "hint": "pip install youtube-transcript-api",
            "video_id": video_id,
        }

    if snippets is None:
        return {
            "ok": False,
            "error": "transcript_unavailable",
            "video_id": video_id,
            "languages_tried": list(languages),
            "errors": errors,
        }

    text = format_transcript_snippets(snippets)
    return {
        "ok": True,
        "video_id": video_id,
        "language": picked_lang,
        "snippet_count": len(snippets),
        "char_count": len(text),
        "text": text,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url_or_id", help="YouTube URL or 11-char video id")
    ap.add_argument("--lang", default="ko,en", help="Comma-separated language preference")
    ap.add_argument("--out", type=Path, default=None, help="Write transcript text file")
    ap.add_argument("--dry-run", action="store_true", help="Validate id only; no network")
    args = ap.parse_args()

    langs = tuple(x.strip() for x in args.lang.split(",") if x.strip())
    result = fetch_youtube_transcript_v0(args.url_or_id, languages=langs, dry_run=args.dry_run)

    if not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1 if result.get("error") != "missing_dependency" else 2

    if args.out and result.get("text"):
        out = args.out if args.out.is_absolute() else ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(str(result["text"]), encoding="utf-8")
        result["out"] = str(out).replace("\\", "/")

    payload = {k: v for k, v in result.items() if k != "text"}
    if args.dry_run or not args.out:
        payload["text_preview"] = str(result.get("text") or "")[:200]
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
