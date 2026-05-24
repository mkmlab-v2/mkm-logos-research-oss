#!/usr/bin/env python3
"""Render radio_dialogue_script_v1 lines to MP3 via edge-tts + ffmpeg concat."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.check_radio_dialogue_script_v1 as gate_mod  # noqa: E402
from scripts.mkm_radio_dialogue_silence_v1 import silence_ms_between  # noqa: E402
from scripts.record_radio_dialogue_signoff_v1 import check_signoff  # noqa: E402

DEFAULT_SCRIPT = ROOT / "reports" / "radio_dialogue_script_morning_shorts_latest.json"
DEFAULT_SIGNOFF = ROOT / "reports" / "radio_dialogue_signoff_latest.json"
DEFAULT_OUT_DIR = ROOT / "reports" / "radio_dialogue_render_latest"
DEFAULT_MERGED = ROOT / "reports" / "radio_dialogue_merged_latest.mp3"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_dialogue(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    for seg in sorted(doc.get("segments") or [], key=lambda s: int(s.get("segment_index") or 0)):
        for d in sorted(seg.get("dialogue") or [], key=lambda x: int(x.get("sequence") or 0)):
            lines.append(d)
    return lines


def _signoff_ok(script_doc: Dict[str, Any], signoff_path: Path) -> Tuple[bool, List[str]]:
    if not signoff_path.is_file():
        return False, ["missing_signoff_file"]
    signoff = _read_json(signoff_path)
    return (len(check_signoff(script_doc, signoff)) == 0, check_signoff(script_doc, signoff))


async def _render_line(text: str, voice: str, out_mp3: Path) -> None:
    import edge_tts  # type: ignore
    from edge_tts.exceptions import NoAudioReceived  # type: ignore

    last_err: Exception | None = None
    for attempt in range(5):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(out_mp3))
            return
        except (NoAudioReceived, Exception) as exc:
            last_err = exc
            await asyncio.sleep(2.0 * (attempt + 1))
    raise last_err or RuntimeError("edge_tts_render_failed")


async def _render_all(
    lines: List[Dict[str, Any]], out_dir: Path, *, use_silence_padding: bool = True
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    prev: Dict[str, Any] | None = None
    for d in lines:
        seq = int(d.get("sequence") or 0)
        persona = str(d.get("persona") or "speaker")
        voice = str(d.get("voice_profile_id") or "ko-KR-SunHiNeural")
        text = str(d.get("audio_text") or "").strip()
        if not text:
            continue
        gap_ms = silence_ms_between(prev, d) if use_silence_padding else 0
        if gap_ms > 0 and paths:
            sil = out_dir / f"{seq:03d}_gap.mp3"
            _ffmpeg_silence_mp3(sil, gap_ms / 1000.0)
            paths.append(sil)
        mp3 = out_dir / f"{seq:03d}_{persona}.mp3"
        await _render_line(text, voice, mp3)
        paths.append(mp3)
        prev = d
        await asyncio.sleep(0.8)
    return paths


def _ffmpeg_silence_mp3(out_mp3: Path, seconds: float) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        str(max(0.1, seconds)),
        "-q:a",
        "9",
        "-acodec",
        "libmp3lame",
        str(out_mp3),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg_silence_failed:{proc.stderr[-300:]}")


def _ffmpeg_concat(mp3_paths: List[Path], merged: Path) -> None:
    if not mp3_paths:
        raise ValueError("no_mp3_segments")
    list_file = merged.parent / "concat_list.txt"
    lines = [f"file '{p.resolve().as_posix()}'" for p in mp3_paths]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(merged),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg_concat_failed:{proc.stderr[-500:]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Render radio dialogue with edge-tts.")
    ap.add_argument("--script-json", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--merged-mp3", type=Path, default=DEFAULT_MERGED)
    ap.set_defaults(require_signoff=True)
    ap.add_argument("--no-require-signoff", action="store_false", dest="require_signoff")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-silence-padding", action="store_true")
    args = ap.parse_args()

    script_path = args.script_json if args.script_json.is_absolute() else ROOT / args.script_json
    doc = _read_json(script_path)
    report = gate_mod.check_radio_dialogue_script(doc)
    if not report.get("gate_ok"):
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    if args.require_signoff:
        signoff_path = args.signoff_json if args.signoff_json.is_absolute() else ROOT / args.signoff_json
        ok, reasons = _signoff_ok(doc, signoff_path)
        if not ok:
            print(json.dumps({"signoff_ok": False, "reasons": reasons}, ensure_ascii=False), file=sys.stderr)
            return 2

    lines = _iter_dialogue(doc)
    if args.dry_run:
        plan = {
            "schema": "radio_dialogue_render_plan_v1",
            "n_lines": len(lines),
            "out_dir": str(args.out_dir),
            "merged_mp3": str(args.merged_mp3),
            "voices": [d.get("voice_profile_id") for d in lines],
        }
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("FAIL: pip install edge-tts", file=sys.stderr)
        return 3

    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    merged = args.merged_mp3 if args.merged_mp3.is_absolute() else ROOT / args.merged_mp3
    merged.parent.mkdir(parents=True, exist_ok=True)

    mp3_paths = asyncio.run(_render_all(lines, out_dir, use_silence_padding=not args.no_silence_padding))
    _ffmpeg_concat(mp3_paths, merged)
    print(str(merged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
