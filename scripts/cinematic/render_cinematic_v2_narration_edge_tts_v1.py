#!/usr/bin/env python3
"""Render cinematic v2 shot narrations via edge-tts → WAV (per shot_plan)."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SHOT_PLAN = ART / "director_agent_v2_shot_plan_latest.json"
DEFAULT_OUT_JSON = ART / "cinematic_v2_narration_render_latest.json"
DEFAULT_VOICE = "ko-KR-SunHiNeural"
DEFAULT_RATE = "-8%"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_shot_plan(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (ROOT / p)


async def render_mp3(text: str, voice: str, rate: str, out_mp3: Path) -> None:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(out_mp3))


def mp3_to_wav(mp3: Path, wav: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp3),
        "-ar",
        "44100",
        "-ac",
        "1",
        str(wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg mp3→wav failed: {r.stderr[:400]}")


def probe_duration_sec(wav: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


async def render_shot(shot: dict, *, voice: str, rate: str, dry_run: bool) -> dict:
    shot_id = str(shot["shot_id"])
    text = str(shot["narration_ko"]).strip()
    wav_target = resolve_path(shot["workspace_targets"]["narration_wav"])
    mp3_temp = wav_target.with_suffix(".mp3")

    row: dict = {
        "shot_id": shot_id,
        "narration_ko": text,
        "voice": voice,
        "rate": rate,
        "wav_path": wav_target.as_posix(),
        "ok": False,
    }

    if dry_run:
        row["ok"] = True
        row["dry_run"] = True
        return row

    wav_target.parent.mkdir(parents=True, exist_ok=True)
    await render_mp3(text, voice, rate, mp3_temp)
    mp3_to_wav(mp3_temp, wav_target)
    if mp3_temp.is_file():
        mp3_temp.unlink()

    duration = probe_duration_sec(wav_target)
    row["duration_sec"] = duration
    row["wav_bytes"] = wav_target.stat().st_size if wav_target.is_file() else 0
    row["ok"] = wav_target.is_file() and row["wav_bytes"] > 0
    return row


async def run_all(
    shots: list[dict],
    *,
    voice: str,
    rate: str,
    dry_run: bool,
) -> list[dict]:
    out: list[dict] = []
    for shot in shots:
        out.append(await render_shot(shot, voice=voice, rate=rate, dry_run=dry_run))
        if not dry_run:
            await asyncio.sleep(0.6)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shot-plan-json", type=Path, default=DEFAULT_SHOT_PLAN)
    ap.add_argument("--shot-id", default="", help="e.g. SHOT_01; empty = all shots")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", default=DEFAULT_RATE, help="edge-tts rate, e.g. -8%%")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shot_plan_path = args.shot_plan_json if args.shot_plan_json.is_absolute() else (ROOT / args.shot_plan_json)
    if not shot_plan_path.is_file():
        raise SystemExit(f"shot plan not found: {shot_plan_path}")

    doc = load_shot_plan(shot_plan_path)
    shots = list(doc.get("shots") or [])
    if args.shot_id:
        shots = [s for s in shots if s.get("shot_id") == args.shot_id]
        if not shots:
            raise SystemExit(f"shot not found: {args.shot_id}")

    if not args.dry_run:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            print(json.dumps({"ok": False, "error": "pip install edge-tts"}, ensure_ascii=False))
            return 1
        ff = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        if ff.returncode != 0:
            print(json.dumps({"ok": False, "error": "ffmpeg not on PATH"}, ensure_ascii=False))
            return 1

    rows = asyncio.run(run_all(shots, voice=args.voice, rate=args.rate, dry_run=args.dry_run))
    ok = all(r.get("ok") for r in rows)

    payload = {
        "schema": "cinematic_v2_narration_render_v1",
        "generated_at_utc": now_utc(),
        "shot_plan_json": str(shot_plan_path.resolve()),
        "voice": args.voice,
        "rate": args.rate,
        "dry_run": args.dry_run,
        "shots": rows,
        "ok": ok,
        "send_gate": "HOLD",
    }

    out_json = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": ok, "out_json": str(out_json), "rendered": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
