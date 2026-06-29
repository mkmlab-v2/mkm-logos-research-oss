#!/usr/bin/env python3
"""Load polluted bench YouTube SSOT + transcript fingerprint helpers [HYPO]."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = ROOT / "tests/fixtures/media_polluted_bench_youtube_ssot_v1.json"


def load_media_polluted_bench_ssot_v0(path: Path | None = None) -> dict[str, Any]:
    ssot_path = path or DEFAULT_SSOT
    if not ssot_path.is_absolute():
        ssot_path = ROOT / ssot_path
    doc = json.loads(ssot_path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "media_polluted_bench_youtube_ssot_v1":
        raise ValueError("invalid polluted bench ssot schema")
    return doc


def resolve_polluted_bench_youtube_url(ssot: dict[str, Any]) -> str | None:
    env_key = str(ssot.get("youtube_url_env") or "MKM_POLLUTED_BENCH_YOUTUBE_URL")
    from_env = os.environ.get(env_key, "").strip()
    if from_env:
        return from_env
    raw = ssot.get("youtube_url")
    if raw:
        return str(raw).strip()
    return None


def transcript_fingerprint_v0(
    text: str,
    keywords: list[str],
    *,
    min_hits: int = 1,
) -> dict[str, Any]:
    hits = {k: k in text for k in keywords if k}
    hit_count = sum(1 for ok in hits.values() if ok)
    return {
        "keywords": keywords,
        "hits": hits,
        "hit_count": hit_count,
        "min_hits": min_hits,
        "pass": hit_count >= min_hits,
        "char_count": len(text),
    }


def read_fixture_transcript(ssot: dict[str, Any]) -> str:
    rel = str(ssot.get("fixture_transcript") or "")
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f"fixture transcript missing: {rel}")
    return path.read_text(encoding="utf-8-sig")
