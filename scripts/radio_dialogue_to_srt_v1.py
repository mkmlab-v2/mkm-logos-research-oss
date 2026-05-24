#!/usr/bin/env python3
"""Convert radio_dialogue_script_v1 dialogue lines to SRT (burn-in / Shorts)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "radio_dialogue_script_morning_shorts_latest.json"
DEFAULT_OUT = ROOT / "reports" / "radio_dialogue_script_morning_shorts_latest.srt"

# Korean TTS ~ chars per second (conservative)
_CHARS_PER_SEC = 14.0
_GAP_SEC = 0.35


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_lines(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    for seg in sorted(doc.get("segments") or [], key=lambda s: int(s.get("segment_index") or 0)):
        for d in sorted(seg.get("dialogue") or [], key=lambda x: int(x.get("sequence") or 0)):
            lines.append(d)
    return lines


def _duration_sec(line: Dict[str, Any]) -> float:
    explicit = line.get("target_duration_sec")
    if isinstance(explicit, (int, float)) and explicit > 0:
        return float(explicit)
    text = str(line.get("audio_text") or "")
    return max(2.0, len(text) / _CHARS_PER_SEC)


def _fmt_ts(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(doc: Dict[str, Any]) -> str:
    blocks: List[str] = []
    t = 0.0
    idx = 1
    for line in _iter_lines(doc):
        dur = _duration_sec(line)
        start = t
        end = t + dur
        persona = line.get("persona") or "speaker"
        text = str(line.get("audio_text") or "").strip()
        text = re.sub(r"\s+", " ", text)
        body = f"[{persona}] {text}" if persona != "system_announcer" else text
        blocks.append(
            f"{idx}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{body}\n"
        )
        idx += 1
        t = end + _GAP_SEC
    return "\n".join(blocks).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="radio_dialogue_script_v1 → SRT")
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-srt", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    path = args.in_json if args.in_json.is_absolute() else ROOT / args.in_json
    doc = _read_json(path)
    srt = build_srt(doc)
    if args.stdout_only:
        print(srt, end="")
        return 0
    out = args.out_srt if args.out_srt.is_absolute() else ROOT / args.out_srt
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(srt, encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
