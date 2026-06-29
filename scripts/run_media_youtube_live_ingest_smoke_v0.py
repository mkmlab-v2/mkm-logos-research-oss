#!/usr/bin/env python3
"""Live YouTube URL fetch + parse/ingest smoke [HYPO · research_only]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_youtube_transcript_v0 import extract_youtube_video_id, fetch_youtube_transcript_v0
from scripts.parse_youtube_transcript_segments_v0 import (
    parse_youtube_transcript_to_segments,
    split_youtube_transcript_blocks,
)

DEFAULT_OUT = ROOT / "reports/media_youtube_live_ingest_smoke_v0_latest.json"
DEFAULT_SMOKE_URL = "https://youtu.be/jNQXAC9IVRw"
FULL_CHAIN = ROOT / "scripts/run_media_youtube_full_ingest_chain_v1.py"
CLOSURE = ROOT / "scripts/verify_handoff_closure_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run_live_smoke(
    url_or_id: str,
    *,
    languages: tuple[str, ...] = ("en", "ko"),
    task_id: str = "YT-LIVE-SMOKE",
    run_full_chain: bool = False,
    verify_closure: bool = False,
) -> dict[str, Any]:
    video_id = extract_youtube_video_id(url_or_id)
    fetch = fetch_youtube_transcript_v0(url_or_id, languages=languages, dry_run=False)
    doc: dict[str, Any] = {
        "schema": "media_youtube_live_ingest_smoke_v0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "input": url_or_id,
        "video_id": video_id,
        "fetch": {k: v for k, v in fetch.items() if k != "text"},
        "ok": False,
        "reproduce": "py scripts/run_media_youtube_live_ingest_smoke_v0.py --help",
    }

    if not fetch.get("ok"):
        doc["error"] = fetch.get("error")
        doc["fetch"] = fetch
        return doc

    text = str(fetch.get("text") or "")
    blocks = split_youtube_transcript_blocks(text)
    segments = parse_youtube_transcript_to_segments(text, min_chars=40, max_chars=280)
    doc["parse"] = {
        "char_count": len(text),
        "block_count": len(blocks),
        "segment_count": len(segments),
        "text_preview": text[:240],
    }
    doc["ok"] = len(blocks) >= 1 and len(segments) >= 1

    chain: dict[str, Any] | None = None
    closure: dict[str, Any] | None = None

    if run_full_chain and doc["ok"]:
        proc = subprocess.run(
            [
                sys.executable,
                str(FULL_CHAIN),
                "--youtube-url",
                url_or_id,
                "--lang",
                ",".join(languages),
                "--task-id",
                task_id,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        chain = {
            "exit_code": proc.returncode,
            "tail": (proc.stdout or proc.stderr).strip().splitlines()[-1:] or [],
        }
        doc["ok"] = proc.returncode == 0
        doc["task_id"] = task_id

    if verify_closure and doc.get("task_id"):
        proc = subprocess.run(
            [
                sys.executable,
                str(CLOSURE),
                "--task-id",
                str(doc["task_id"]),
                "--dry-run",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        closure = {
            "exit_code": proc.returncode,
            "tail": (proc.stdout or proc.stderr).strip().splitlines()[-1:] or [],
        }
        doc["ok"] = doc.get("ok", False) and proc.returncode == 0

    doc["chain"] = chain
    doc["closure"] = closure
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--youtube-url", default=DEFAULT_SMOKE_URL)
    ap.add_argument("--lang", default="en,ko")
    ap.add_argument("--task-id", default="YT-LIVE-SMOKE")
    ap.add_argument("--full-chain", action="store_true", help="Run full ingest + handoff after fetch")
    ap.add_argument("--verify-closure", action="store_true", help="Run handoff closure dry-run")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    langs = tuple(x.strip() for x in args.lang.split(",") if x.strip())
    doc = run_live_smoke(
        args.youtube_url,
        languages=langs,
        task_id=args.task_id,
        run_full_chain=args.full_chain,
        verify_closure=args.verify_closure,
    )

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": doc.get("ok"),
                "report": _rel(out),
                "video_id": doc.get("video_id"),
                "blocks": (doc.get("parse") or {}).get("block_count"),
                "segments": (doc.get("parse") or {}).get("segment_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
