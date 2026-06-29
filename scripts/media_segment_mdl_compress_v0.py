#!/usr/bin/env python3
"""B-track [HYPO] — lightweight MDL-style compression for media transcript segments."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_FILLERS: tuple[str, ...] = (
    "어",
    "음",
    "그",
    "저",
    "저기",
    "그러니까",
    "뭐",
    "약간",
    "잉",
)

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _tokens(text: str) -> set[str]:
    return {w for w in re.split(r"\s+", text.strip()) if len(w) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compress_media_text_mdl_v0(
    text: str,
    *,
    anchor_keywords: list[str] | None = None,
    fillers: tuple[str, ...] = DEFAULT_FILLERS,
) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {
            "raw_chars": 0,
            "compressed_chars": 0,
            "char_saving_rate": 0.0,
            "token_jaccard": 1.0,
            "compressed_text": "",
            "steps_applied": [],
        }

    steps: list[str] = []
    body = raw

    for f in fillers:
        body = body.replace(f"{f}...", " ")
        body = body.replace(f"{f}.", " ")
        body = re.sub(rf"{re.escape(f)}(?=[\s,.!?…]|$)", " ", body)
    body = re.sub(r"\.{2,}", ".", body)
    body = re.sub(r"\s+", " ", body).strip()
    steps.append("filler_strip")

    kws = [k for k in (anchor_keywords or []) if k]
    if kws:
        kept: list[str] = []
        for sent in [s.strip() for s in _SENT_SPLIT.split(body) if s.strip()]:
            if any(k in sent for k in kws):
                kept.append(sent)
        if kept:
            body = " ".join(kept)
            steps.append("anchor_sentence_filter")
    else:
        steps.append("anchor_sentence_filter_skipped")

    body = re.sub(r"\s+", " ", body).strip()
    raw_tokens = _tokens(raw)
    comp_tokens = _tokens(body)
    raw_chars = len(raw)
    comp_chars = len(body)
    saving = 0.0 if raw_chars == 0 else round(1.0 - (comp_chars / raw_chars), 4)

    return {
        "raw_chars": raw_chars,
        "compressed_chars": comp_chars,
        "char_saving_rate": saving,
        "token_jaccard": round(_jaccard(raw_tokens, comp_tokens), 4),
        "compressed_text": body,
        "steps_applied": steps,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", default=None)
    ap.add_argument("--from-json-segment", type=Path, default=None)
    ap.add_argument("--segment-id", default=None)
    ap.add_argument("--anchors", default="")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    text = args.text or ""
    anchors = [k.strip() for k in args.anchors.split(",") if k.strip()]

    if args.from_json_segment:
        doc = json.loads(args.from_json_segment.read_text(encoding="utf-8-sig"))
        seg_id = args.segment_id
        segments = doc.get("segments") or []
        picked = None
        if seg_id:
            picked = next((s for s in segments if s.get("id") == seg_id), None)
        if picked is None and segments:
            picked = segments[0]
        if picked is None:
            print(json.dumps({"ok": False, "error": "segment_not_found"}), file=sys.stderr)
            return 1
        text = str(picked.get("text") or "")
        if not anchors:
            anchors = list(doc.get("theme_keywords") or [])

    result = compress_media_text_mdl_v0(text, anchor_keywords=anchors)
    report = {
        "schema": "media_segment_mdl_compress_v0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        **result,
        "reproduce": "py scripts/media_segment_mdl_compress_v0.py --help",
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
