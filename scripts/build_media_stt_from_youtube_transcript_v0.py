#!/usr/bin/env python3
"""Build media_stt_transcription_v1 from raw YouTube transcript text [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parse_youtube_transcript_segments_v0 import parse_youtube_transcript_to_segments

DEFAULT_OUT = ROOT / "reports/forensics/stt_transcription_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/media_stt_transcription_v1.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_doc_from_youtube_text(
    transcript: str,
    *,
    theme: str,
    wav_source: str,
    target_suite: str,
    theme_keywords: list[str],
    negative_keywords: list[str],
    multilens_keywords: list[str],
    merge_min_chars: int = 40,
    merge_max_chars: int = 280,
) -> dict[str, Any]:
    segments = parse_youtube_transcript_to_segments(
        transcript,
        min_chars=merge_min_chars,
        max_chars=merge_max_chars,
    )
    if not segments:
        raise ValueError("no segments parsed from youtube transcript")
    return {
        "schema": "media_stt_transcription_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "stt_engine": "youtube_transcript_parse_v0",
        "wav_source": wav_source,
        "theme": theme,
        "target_suite": target_suite,
        "theme_keywords": theme_keywords,
        "negative_keywords": negative_keywords,
        "multilens_keywords": multilens_keywords,
        "segments": segments,
        "reproduce": "py scripts/build_media_stt_from_youtube_transcript_v0.py --help",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--theme", default="성경 기원 논쟁 (YouTube transcript ingest)")
    ap.add_argument("--wav-source", default="fixture://youtube_transcript_v0 (no WAV)")
    ap.add_argument("--target-suite", default="CapCut & AntiGravity [YT_INGEST]")
    ap.add_argument(
        "--theme-keywords",
        default="조로,엘로힘,유수,바빌론,페르시아,다신교,종교학,학자,메시지",
    )
    ap.add_argument(
        "--negative-keywords",
        default="시친,니비루,아누나키,이시스,외계인,뇌피셜",
    )
    ap.add_argument(
        "--multilens-keywords",
        default="뱀,에덴,릴리스,오피,프로메테우스,루시퍼,지혜,선악",
    )
    ap.add_argument("--merge-min-chars", type=int, default=40)
    ap.add_argument("--merge-max-chars", type=int, default=280)
    ap.add_argument("--strict-schema", action="store_true")
    ap.add_argument("--chain-handoff", action="store_true")
    ap.add_argument("--task-id", default="20260621-YT-INGEST")
    args = ap.parse_args()

    src = args.input if args.input.is_absolute() else ROOT / args.input
    if not src.is_file():
        print(json.dumps({"ok": False, "error": "input_missing", "path": str(src)}), file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8-sig")
    kws = [k.strip() for k in args.theme_keywords.split(",") if k.strip()]
    neg = [k.strip() for k in args.negative_keywords.split(",") if k.strip()]
    ml = [k.strip() for k in args.multilens_keywords.split(",") if k.strip()]

    try:
        doc = build_doc_from_youtube_text(
            text,
            theme=args.theme,
            wav_source=args.wav_source,
            target_suite=args.target_suite,
            theme_keywords=kws,
            negative_keywords=neg,
            multilens_keywords=ml,
            merge_min_chars=args.merge_min_chars,
            merge_max_chars=args.merge_max_chars,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    if args.strict_schema:
        try:
            import jsonschema
        except ImportError:
            pass
        else:
            schema = json.loads(SCHEMA.read_text(encoding="utf-8-sig"))
            jsonschema.Draft7Validator(schema).validate(doc)

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chain_ok = None
    if args.chain_handoff:
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_media_handoff_worker_v1.py"),
                "--task-id",
                args.task_id,
                "--source",
                str(out),
                "--strict-schema",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        chain_ok = proc.returncode == 0
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return 2

    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(out),
                "segments": len(doc["segments"]),
                "chain_handoff": chain_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
