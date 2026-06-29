#!/usr/bin/env python3
"""One-click: full YouTube transcript -> diff report -> handoff [HYPO]."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "tests/fixtures/youtube_transcript_polluted_full_v0.txt"
DIFF = ROOT / "scripts/build_media_youtube_ingest_diff_report_v0.py"
FETCH = ROOT / "scripts/fetch_youtube_transcript_v0.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=None, help="Local transcript txt (default fixture)")
    ap.add_argument("--youtube-url", default=None, help="Fetch captions first (requires youtube-transcript-api)")
    ap.add_argument("--lang", default="ko,en")
    ap.add_argument("--task-id", default="20260621-YT-FULL")
    ap.add_argument("--merge-min-chars", type=int, default=650)
    ap.add_argument("--merge-max-chars", type=int, default=1300)
    args = ap.parse_args()

    src: Path | None = None
    temp_path: Path | None = None

    if args.youtube_url:
        fetch_cmd = [
            sys.executable,
            str(FETCH),
            args.youtube_url,
            "--lang",
            args.lang,
            "--out",
        ]
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            temp_path = Path(tmp.name)
        fetch_cmd.append(str(temp_path))
        proc = subprocess.run(fetch_cmd, cwd=str(ROOT), capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            if temp_path and temp_path.is_file():
                temp_path.unlink(missing_ok=True)
            return proc.returncode or 1
        src = temp_path
    else:
        src = args.input if args.input else DEFAULT_INPUT
        src = src if src.is_absolute() else ROOT / src

    cmd = [
        sys.executable,
        str(DIFF),
        "--input",
        str(src),
        "--task-id",
        args.task_id,
        "--merge-min-chars",
        str(args.merge_min_chars),
        "--merge-max-chars",
        str(args.merge_max_chars),
        "--chain-handoff",
    ]
    if args.youtube_url:
        cmd.extend(["--wav-source", f"youtube://{args.youtube_url}"])

    try:
        return subprocess.call(cmd, cwd=str(ROOT))
    finally:
        if temp_path and temp_path.is_file():
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())