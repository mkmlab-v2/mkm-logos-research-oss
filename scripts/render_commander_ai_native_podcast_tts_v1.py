#!/usr/bin/env python3
"""Render commander AI-native podcast script MD to MP3 via edge-tts [HYPO] Plane C."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCRIPT = ART / "commander_ai_native_podcast_script_latest.md"
DEFAULT_OUT_MP3 = ROOT / "reports" / "commander_ai_native_podcast_latest.mp3"
DEFAULT_OUT_JSON = ART / "commander_ai_native_podcast_tts_latest.json"
DEFAULT_VOICE = "ko-KR-InJoonNeural"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_narration_text(md_path: Path) -> str:
    lines: list[str] = []
    for raw in md_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        if line.startswith("**") and line.endswith("**"):
            continue
        if line.startswith("`"):
            continue
        if line.startswith("### "):
            line = line.removeprefix("### ").strip()
        lines.append(line)
    text = " ".join(lines)
    return re.sub(r"\s+", " ", text).strip()


async def _render_mp3(text: str, voice: str, out_mp3: Path) -> None:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_mp3))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--script-md", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--out-mp3", type=Path, default=DEFAULT_OUT_MP3)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    script_path = args.script_md if args.script_md.is_absolute() else ROOT / args.script_md
    if not script_path.is_file():
        raise SystemExit(f"Missing script: {script_path}")

    text = extract_narration_text(script_path)
    if len(text) < 40:
        raise SystemExit("Narration text too short after MD extract")

    out_mp3 = args.out_mp3 if args.out_mp3.is_absolute() else ROOT / args.out_mp3
    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json

    payload: dict[str, object] = {
        "schema": "commander_ai_native_podcast_tts_v1",
        "generated_at_utc": _utc_now(),
        "dry_run": args.dry_run,
        "script_md": str(script_path.resolve()),
        "voice": args.voice,
        "char_count": len(text),
        "track_wall": {
            "lane": "internal_observation_only",
            "human_publish_only": True,
            "send_gate": "HOLD",
            "patient_facing_auto_copy": False,
        },
    }

    if args.dry_run:
        payload["out_mp3"] = str(out_mp3.resolve())
        payload["text_preview"] = text[:240]
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "out_json": str(out_json)}, ensure_ascii=False))
        return 0

    try:
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(_render_mp3(text, args.voice, out_mp3))
    except ImportError:
        print(json.dumps({"ok": True, "skipped": True, "reason": "edge_tts_not_installed"}, ensure_ascii=False))
        return 0
    except Exception as exc:  # pragma: no cover
        print(json.dumps({"ok": False, "error": str(exc)[:200]}, ensure_ascii=False))
        return 1

    payload["out_mp3"] = str(out_mp3.resolve())
    payload["mp3_bytes"] = out_mp3.stat().st_size if out_mp3.is_file() else 0
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_mp3": str(out_mp3), "out_json": str(out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
