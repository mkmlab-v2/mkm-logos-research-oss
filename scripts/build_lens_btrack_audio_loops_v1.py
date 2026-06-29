#!/usr/bin/env python3
"""Bake 12 lens B-track audio loops (tone bed) from playback LUT matrix."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_btrack_playback_matrix_v1 import (  # noqa: E402
    audio_filename,
    audio_playback_id,
    build_audio_lut,
    iter_matrix_pairs,
    target_bpm,
)

DEFAULT_OUT_DIR = ROOT / "reports" / "track_c_audio_hook_samples_v1"
LUT_LATEST = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_tone_wav(path: Path, *, seconds: float, hz: float, sample_rate: int = 48000) -> None:
    n = max(2, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    amp = 5500.0
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        denom = max(1.0, float(n - 1))
        for i in range(n):
            env = math.sin(math.pi * i / denom)
            s = amp * env * math.sin(2.0 * math.pi * hz * (i / float(sample_rate)))
            v = int(max(-32767, min(32767, round(s))))
            wf.writeframes(struct.pack("<h", v))


def _hz_from_bpm(bpm: float) -> float:
    base = 55.0 + (bpm % 37) * 2.0
    return min(max(base, 55.0), 880.0)


def _lut_entries() -> list[tuple[str, str, str, int, str]]:
    lut: dict[str, Any] = {}
    if LUT_LATEST.is_file():
        lut = json.loads(LUT_LATEST.read_text(encoding="utf-8"))
    if lut.get("schema") != "jemaai_lens_audio_playback_lut_v1":
        lut = build_audio_lut()
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    rows: list[tuple[str, str, str, int, str]] = []
    for pid, row in entries.items():
        if not isinstance(row, dict):
            continue
        sasang = str(row.get("sasang_primary") or "soyang")
        mode = str(row.get("showroom_display_mode") or "idle")
        fname = str(row.get("file") or "")
        dur = int(row.get("duration_sec") or 30)
        if fname:
            rows.append((str(pid), sasang, mode, dur, fname))
    if rows:
        return rows
    return [
        (audio_playback_id(s, m), s, m, 30, audio_filename(s, m))
        for s, m in iter_matrix_pairs()
    ]


def main() -> int:
    p = argparse.ArgumentParser(description="Bake lens B-track audio loop samples (stdlib tone)")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    report: dict[str, Any] = {
        "schema": "lens_btrack_audio_bake_report_v1",
        "generated_at_utc": _utc_now_z(),
        "out_dir": str(args.out_dir),
        "clips": [],
    }

    failed = 0
    for pid, sasang, mode, duration_sec, fname in _lut_entries():
        out_wav = args.out_dir / fname
        bpm = target_bpm(sasang, mode)
        hz = _hz_from_bpm(bpm)
        clip: dict[str, Any] = {
            "playback_id": pid,
            "sasang_primary": sasang,
            "showroom_display_mode": mode,
            "file": fname,
            "bpm_target": bpm,
            "hz": hz,
        }
        if args.dry_run:
            clip["status"] = "dry_run"
            report["clips"].append(clip)
            continue
        _write_tone_wav(out_wav, seconds=float(duration_sec), hz=hz)
        ok = out_wav.is_file() and out_wav.stat().st_size > 0
        clip["status"] = "ok" if ok else "fail"
        if not ok:
            failed += 1
        report["clips"].append(clip)
        print(f"[lens-audio-bake] {pid} -> {fname} bpm={bpm:.1f} hz={hz:.1f}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "lens_btrack_audio_bake_report_v1_latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-audio-bake] WROTE: {report_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
