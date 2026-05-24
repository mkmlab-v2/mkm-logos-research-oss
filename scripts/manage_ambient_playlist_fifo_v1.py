#!/usr/bin/env python3
"""Zone A FFmpeg concat demuxer FIFO — bed loop + Zone B event inject."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAYLIST = ROOT / "reports" / "ambient_stream_playlist_fifo.txt"
DEFAULT_STATE = ROOT / "reports" / "ambient_stream_playlist_fifo_state_latest.json"
DEFAULT_BED = ROOT / "reports" / "audio" / "mkm_ambient_bed_loop_latest.wav"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_state(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"entries": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_playlist(entries: List[Dict[str, Any]], playlist_path: Path) -> None:
    lines: List[str] = []
    for e in entries:
        p = e.get("path_posix") or e.get("path")
        if p:
            lines.append(f"file '{p}'")
    playlist_path.parent.mkdir(parents=True, exist_ok=True)
    playlist_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def init_fifo(root: Path, bed: Path, *, playlist_path: Path) -> Dict[str, Any]:
    bed_abs = bed if bed.is_absolute() else root / bed
    if not bed_abs.is_file():
        raise FileNotFoundError(bed_abs)
    rel = _posix(bed_abs, root)
    entries = [
        {
            "kind": "zone_a_bed",
            "path_posix": rel,
            "added_at_utc": _utc_now(),
        }
    ]
    _write_playlist(entries, playlist_path)
    return {"schema": "ambient_playlist_fifo_state_v1", "entries": entries, "updated_at_utc": _utc_now()}


def append_event(root: Path, media: Path, *, kind: str, playlist_path: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    media_abs = media if media.is_absolute() else root / media
    if not media_abs.is_file():
        raise FileNotFoundError(media_abs)
    rel = _posix(media_abs, root)
    entries = list(state.get("entries") or [])
    entries.append({"kind": kind, "path_posix": rel, "added_at_utc": _utc_now()})
    _write_playlist(entries, playlist_path)
    return {"schema": "ambient_playlist_fifo_state_v1", "entries": entries, "updated_at_utc": _utc_now()}


def emit_ffmpeg_concat_cmd(playlist_path: Path, *, copy_audio: bool = True) -> str:
    codec = "-c copy" if copy_audio else "-c:a aac -b:a 128k"
    return (
        f"ffmpeg -y -f concat -safe 0 -i \"{playlist_path.resolve()}\" "
        f"{codec} -f null -"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Ambient concat FIFO playlist manager.")
    ap.add_argument("command", choices=["init", "append", "emit-cmd", "status"])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--bed-wav", type=Path, default=DEFAULT_BED)
    ap.add_argument("--media", type=Path, default=None, help="append: zone B mp3/wav")
    ap.add_argument("--kind", type=str, default="zone_b_event")
    ap.add_argument("--playlist-txt", type=Path, default=DEFAULT_PLAYLIST)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    args = ap.parse_args()

    playlist = args.playlist_txt if args.playlist_txt.is_absolute() else args.root / args.playlist_txt
    state_path = args.state_json if args.state_json.is_absolute() else args.root / args.state_json

    if args.command == "init":
        doc = init_fifo(args.root, args.bed_wav, playlist_path=playlist)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(playlist))
        return 0

    if args.command == "append":
        if not args.media:
            print("FAIL: --media required", file=sys.stderr)
            return 2
        state = _read_state(state_path)
        if not state.get("entries"):
            state = init_fifo(args.root, args.bed_wav, playlist_path=playlist)
        doc = append_event(args.root, args.media, kind=args.kind, playlist_path=playlist, state=state)
        state_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(playlist))
        return 0

    if args.command == "emit-cmd":
        if not playlist.is_file():
            print("FAIL: playlist missing; run init first", file=sys.stderr)
            return 2
        print(emit_ffmpeg_concat_cmd(playlist))
        return 0

    if args.command == "status":
        st = _read_state(state_path) if state_path.is_file() else {}
        print(
            json.dumps(
                {
                    "playlist": str(playlist),
                    "playlist_exists": playlist.is_file(),
                    "n_entries": len(st.get("entries") or []),
                    "entries": st.get("entries") or [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
