#!/usr/bin/env python3
"""S2_LIVE_EDIT v1: Whisper-guided smart cut editor for presentation videos.

Pipeline (v1)
1) Transcribe with faster-whisper (word timestamps preferred)
2) Remove filler-word regions ("아", "어", "그니까", ...)
3) Build keep intervals + ffmpeg concat filter
4) Optionally render edited mp4

Notes
- This is a deterministic, script-first baseline (Fact-Lock friendly).
- Requires local ffmpeg/ffprobe binaries in PATH.
- Requires Python package: faster-whisper
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "reports" / "video_edit"

# Conservative default list; user can override with --filler-json.
DEFAULT_FILLERS = {
    "아",
    "어",
    "음",
    "그",
    "그냥",
    "이제",
    "저기",
    "뭐",
    "약간",
    "사실",
    "그니까",
    "그러니까",
    "you know",
    "like",
    "uh",
    "um",
}


@dataclass(frozen=True)
class Span:
    start: float
    end: float

    def clamp(self, lo: float, hi: float) -> "Span":
        return Span(start=max(lo, min(self.start, hi)), end=max(lo, min(self.end, hi)))

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        raise RuntimeError(f"Missing required tools in PATH: {', '.join(missing)}")


def ffprobe_duration(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def normalize_token(token: str) -> str:
    return token.strip().strip(".,!?\"'()[]{}").lower()


def load_fillers(path: Path | None) -> set[str]:
    if path is None:
        return set(DEFAULT_FILLERS)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {normalize_token(str(x)) for x in data}
    raise ValueError("filler json must be a JSON array of strings")


def try_transcribe_words(video_path: Path, model_name: str, beam_size: int) -> list[dict]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "faster-whisper is not installed. Install with:\n"
            "  py -m pip install faster-whisper\n"
        ) from exc

    model = WhisperModel(model_name, device="auto", compute_type="auto")
    segments, _info = model.transcribe(
        str(video_path),
        beam_size=beam_size,
        vad_filter=True,
        word_timestamps=True,
        language="ko",
    )

    words: list[dict] = []
    for seg in segments:
        seg_words = getattr(seg, "words", None) or []
        for w in seg_words:
            token = normalize_token(getattr(w, "word", ""))
            start = float(getattr(w, "start", 0.0))
            end = float(getattr(w, "end", 0.0))
            if end > start:
                words.append({"word": token, "start": start, "end": end})
    if not words:
        raise RuntimeError("No word timestamps found from whisper output.")
    return words


def merge_spans(spans: Iterable[Span], join_gap: float) -> list[Span]:
    items = sorted((s for s in spans if s.end > s.start), key=lambda s: s.start)
    if not items:
        return []
    merged: list[Span] = [items[0]]
    for s in items[1:]:
        prev = merged[-1]
        if s.start <= prev.end + join_gap:
            merged[-1] = Span(prev.start, max(prev.end, s.end))
        else:
            merged.append(s)
    return merged


def invert_to_keep(cuts: list[Span], total_dur: float, min_keep: float) -> list[Span]:
    if not cuts:
        return [Span(0.0, total_dur)]
    keeps: list[Span] = []
    cursor = 0.0
    for c in cuts:
        if c.start > cursor:
            k = Span(cursor, c.start)
            if k.duration >= min_keep:
                keeps.append(k)
        cursor = max(cursor, c.end)
    if cursor < total_dur:
        k = Span(cursor, total_dur)
        if k.duration >= min_keep:
            keeps.append(k)
    return keeps


def build_filter_complex(keeps: list[Span]) -> str:
    parts: list[str] = []
    for i, s in enumerate(keeps):
        parts.append(f"[0:v]trim=start={s.start:.3f}:end={s.end:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={s.start:.3f}:end={s.end:.3f},asetpts=PTS-STARTPTS[a{i}]")
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(keeps)))
    parts.append(f"{concat_inputs}concat=n={len(keeps)}:v=1:a=1[v][a]")
    return ";".join(parts)


def render_video(video_path: Path, out_mp4: Path, filter_complex: str, crf: int, preset: str) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out_mp4),
    ]
    subprocess.check_call(cmd)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Whisper-guided smart cut editor (S2_LIVE_EDIT v1).")
    ap.add_argument("--input-video", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--model", default="small")
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--filler-json", type=Path, default=None, help="JSON array of filler tokens")
    ap.add_argument("--pad-left", type=float, default=0.06)
    ap.add_argument("--pad-right", type=float, default=0.08)
    ap.add_argument("--join-gap", type=float, default=0.10)
    ap.add_argument("--min-keep-seconds", type=float, default=0.20)
    ap.add_argument("--render", action="store_true", help="Render edited mp4 with ffmpeg")
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--preset", default="medium")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_tools()
    in_video = args.input_video.resolve()
    if not in_video.is_file():
        raise FileNotFoundError(f"Input video not found: {in_video}")

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = in_video.stem
    out_json = out_dir / f"{stem}.s2_live_edit_cutplan_v1.json"
    out_txt = out_dir / f"{stem}.s2_live_edit_ffmpeg_filter_v1.txt"
    out_mp4 = out_dir / f"{stem}.s2_live_edit_v1.mp4"

    total_dur = ffprobe_duration(in_video)
    fillers = load_fillers(args.filler_json)
    words = try_transcribe_words(in_video, model_name=args.model, beam_size=args.beam_size)

    raw_cuts: list[Span] = []
    for w in words:
        if w["word"] in fillers:
            raw_cuts.append(
                Span(
                    start=max(0.0, float(w["start"]) - args.pad_left),
                    end=min(total_dur, float(w["end"]) + args.pad_right),
                )
            )

    merged_cuts = merge_spans(raw_cuts, join_gap=args.join_gap)
    keeps = invert_to_keep(merged_cuts, total_dur=total_dur, min_keep=args.min_keep_seconds)

    if not keeps:
        keeps = [Span(0.0, total_dur)]

    filter_complex = build_filter_complex(keeps)

    doc = {
        "schema": "s2_live_edit_whisper_cutplan_v1",
        "generated_at_utc": utc_now(),
        "input_video": str(in_video),
        "model": args.model,
        "beam_size": args.beam_size,
        "video_duration_sec": total_dur,
        "filler_count_detected": len(raw_cuts),
        "cut_segments": [{"start": round(s.start, 3), "end": round(s.end, 3)} for s in merged_cuts],
        "keep_segments": [{"start": round(s.start, 3), "end": round(s.end, 3)} for s in keeps],
        "rendered": False,
        "output_video": str(out_mp4),
    }

    if args.render:
        render_video(in_video, out_mp4=out_mp4, filter_complex=filter_complex, crf=args.crf, preset=args.preset)
        doc["rendered"] = True

    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_txt.write_text(filter_complex + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "cutplan_json": str(out_json),
                "filter_txt": str(out_txt),
                "rendered": bool(doc["rendered"]),
                "output_video": str(out_mp4),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
