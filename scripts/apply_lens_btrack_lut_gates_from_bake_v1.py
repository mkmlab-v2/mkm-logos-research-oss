#!/usr/bin/env python3
"""Patch lens audio LUT gate_decision from MusicGen/tone bake report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports/track_c_audio_hook_samples_v1/lens_btrack_audio_musicgen_bake_report_v1_latest.json"
FALLBACK_REPORT = ROOT / "reports/track_c_audio_hook_samples_v1/lens_btrack_audio_bake_report_v1_latest.json"
AUDIO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"
AUDIO_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1.example.json"
VIDEO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"
VIDEO_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1.example.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_for_clip(clip: dict[str, Any]) -> str:
    gen = str(clip.get("generator") or "")
    if clip.get("status") != "ok":
        return "FAIL"
    if gen == "musicgen_melody":
        return "PASS"
    return "WATCH"


def _mirror_audio_gates_to_video(audio_lut: dict[str, Any], video_lut: dict[str, Any]) -> int:
    """Copy gate_decision from audio LUT entries onto mirrored video LUT rows."""
    a_entries = audio_lut.get("entries") if isinstance(audio_lut.get("entries"), dict) else {}
    v_entries = video_lut.get("entries") if isinstance(video_lut.get("entries"), dict) else {}
    if not a_entries or not v_entries:
        return 0
    mirror_by_audio: dict[str, str] = {}
    for vid, row in v_entries.items():
        if not isinstance(row, dict):
            continue
        mirror = str(row.get("audio_playback_id_mirror") or "")
        if mirror:
            mirror_by_audio[mirror] = str(vid)
    updated = 0
    for aid, arow in a_entries.items():
        if not isinstance(arow, dict):
            continue
        gate = arow.get("gate_decision")
        if gate is None:
            continue
        vid = mirror_by_audio.get(str(aid)) or str(aid).replace("LM_", "LV_", 1)
        vrow = v_entries.get(vid)
        if not isinstance(vrow, dict):
            continue
        if vrow.get("gate_decision") != gate:
            vrow["gate_decision"] = gate
            vrow["gate_source"] = str(audio_lut.get("gate_sync_report") or "audio_lut_mirror")
            updated += 1
    return updated


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--lut", type=Path, default=AUDIO_LUT)
    ap.add_argument("--video-lut", type=Path, default=VIDEO_LUT)
    ap.add_argument("--skip-video-mirror", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    report_path = args.report
    if report_path is None:
        report_path = DEFAULT_REPORT if DEFAULT_REPORT.is_file() else FALLBACK_REPORT
    report = _load_report(report_path)
    clips = report.get("clips") if isinstance(report.get("clips"), list) else []
    if not clips:
        print(f"[lens-lut-gates] no clips in {report_path}", file=sys.stderr)
        return 2
    if not args.lut.is_file():
        print(f"[lens-lut-gates] missing LUT {args.lut}", file=sys.stderr)
        return 2

    lut = json.loads(args.lut.read_text(encoding="utf-8"))
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    updated = 0
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        pid = str(clip.get("playback_id") or "")
        if pid not in entries:
            continue
        gate = _gate_for_clip(clip)
        row = entries[pid]
        if row.get("gate_decision") != gate:
            row["gate_decision"] = gate
            row["gate_source"] = str(report_path.relative_to(ROOT)).replace("\\", "/")
            updated += 1

    lut["gate_sync_at_utc"] = _utc_now_z()
    lut["gate_sync_report"] = str(report_path.relative_to(ROOT)).replace("\\", "/")
    if report.get("schema") == "lens_btrack_audio_musicgen_bake_report_v1":
        lut["audio_generator"] = "musicgen_melody_v1"

    video_updated = 0
    video_lut: dict[str, Any] | None = None
    if not args.skip_video_mirror and args.video_lut.is_file():
        video_lut = json.loads(args.video_lut.read_text(encoding="utf-8"))
        video_updated = _mirror_audio_gates_to_video(lut, video_lut)
        if video_lut is not None:
            video_lut["gate_sync_at_utc"] = lut["gate_sync_at_utc"]
            video_lut["gate_sync_report"] = lut.get("gate_sync_report")
            video_lut["gate_sync_source"] = "audio_lut_mirror_v1"

    if args.dry_run:
        print(
            json.dumps(
                {"audio_updated": updated, "video_updated": video_updated, "lut": str(args.lut)},
                ensure_ascii=False,
            )
        )
        return 0

    args.lut.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if AUDIO_EXAMPLE.is_file() or args.lut == AUDIO_LUT:
        AUDIO_EXAMPLE.parent.mkdir(parents=True, exist_ok=True)
        AUDIO_EXAMPLE.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[lens-lut-gates] updated {updated} audio entries in {args.lut}")
    if video_lut is not None:
        args.video_lut.write_text(json.dumps(video_lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if VIDEO_EXAMPLE.is_file() or args.video_lut == VIDEO_LUT:
            VIDEO_EXAMPLE.write_text(json.dumps(video_lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[lens-lut-gates] mirrored {video_updated} video entries in {args.video_lut}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
