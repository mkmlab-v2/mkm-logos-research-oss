#!/usr/bin/env python3
"""O-P31c — aggregate latest radio/ambient artifacts into one ops summary JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "radio_op31c_daily_summary_latest.json"

PATHS = {
    "logos_anchor": "reports/commander_daily_logos_anchor_latest.json",
    "fortune": "reports/commander_daily_fortune_latest.json",
    "briefing": "reports/commander_advanced_briefing_latest.json",
    "morning_script": "reports/radio_dialogue_script_morning_shorts_latest.json",
    "morning_gate": "reports/radio_dialogue_script_gate_morning_latest.json",
    "friday_gate": "reports/radio_dialogue_script_gate_friday_latest.json",
    "morning_mp3": "reports/radio_dialogue_merged_latest.mp3",
    "friday_script": "reports/radio_dialogue_script_friday_vod_latest.json",
    "friday_mp3": "reports/radio_dialogue_friday_merged_latest.mp3",
    "health_script": "reports/radio_dialogue_script_health_shorts_latest.json",
    "health_gate": "reports/radio_dialogue_script_gate_health_latest.json",
    "health_mp3": "reports/radio_dialogue_health_merged_latest.mp3",
    "video_bed": "reports/video/oracle_sphere_idle_loop_latest.mp4",
    "fifo_playlist": "reports/ambient_stream_playlist_fifo.txt",
    "rtmp_command": "reports/ambient_stream_rtmp_command_latest.txt",
    "ambient_bed": "reports/audio/mkm_ambient_bed_loop_latest.wav",
    "ambient_manifest": "reports/ambient_stream_manifest_latest.json",
    "ffmpeg_plan": "reports/ambient_stream_ffmpeg_plan_latest.json",
    "studio_paste": "reports/radio_youtube_studio_paste_latest.txt",
    "youtube_channel_copy": "docs/final/artifacts/radio_youtube_channel_copy_v1_latest.json",
    "friday_srt": "reports/radio_dialogue_script_friday_vod_latest.srt",
    "morning_srt": "reports/radio_dialogue_script_morning_shorts_latest.srt",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _file_row(root: Path, rel: str) -> Dict[str, Any]:
    p = root / rel
    row: Dict[str, Any] = {"path": rel, "exists": p.is_file()}
    if p.is_file():
        row["bytes"] = p.stat().st_size
    return row


def _rtmp_command_live(root: Path) -> bool:
    cmd_path = root / PATHS["rtmp_command"]
    if not cmd_path.is_file():
        return False
    first = cmd_path.read_text(encoding="utf-8").splitlines()[0].strip() if cmd_path.stat().st_size else ""
    if first.startswith("#") or "<RTMP_URL>" in first:
        return False
    meta_path = cmd_path.with_suffix(".meta.json")
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        if meta.get("rtmp_configured") is True:
            return True
    return first.startswith("ffmpeg")


def _rtmp_url_configured(root: Path, plan: Dict[str, Any]) -> bool:
    if bool(plan.get("rtmp_url_set")):
        return True
    if (os.environ.get("YOUTUBE_RTMP_URL") or "").strip():
        return True
    if _rtmp_command_live(root):
        return True
    return False


def _live_stage(rtmp_ok: bool, smoke_ok: bool | None) -> str:
    if smoke_ok is True:
        return "L3_rtmp_smoke_ok"
    if rtmp_ok:
        return "L1_rtmp_wired"
    return "L0_content_only"


def build_summary(root: Path) -> Dict[str, Any]:
    files = {k: _file_row(root, v) for k, v in PATHS.items()}
    gate_m = _read_json(root / PATHS["morning_gate"])
    gate_f = _read_json(root / PATHS["friday_gate"])
    gate_h = _read_json(root / PATHS["health_gate"])
    morning = _read_json(root / PATHS["morning_script"])
    friday = _read_json(root / PATHS["friday_script"])
    health = _read_json(root / PATHS["health_script"])
    plan = _read_json(root / PATHS["ffmpeg_plan"])
    rtmp_ok = _rtmp_url_configured(root, plan)
    smoke_path = root / "reports" / "ambient_stream_rtmp_smoke_latest.json"
    smoke_doc = _read_json(smoke_path) if smoke_path.is_file() else {}
    smoke_ok: bool | None = smoke_doc.get("ok") if smoke_doc else None

    required_keys = [
        "logos_anchor",
        "fortune",
        "briefing",
        "morning_script",
        "morning_gate",
        "friday_gate",
        "ambient_bed",
        "ambient_manifest",
        "health_script",
        "health_gate",
    ]
    missing: List[str] = [k for k in required_keys if not files.get(k, {}).get("exists")]
    ok = (
        not missing
        and gate_m.get("gate_ok") is True
        and gate_f.get("gate_ok") is True
        and gate_h.get("gate_ok") is True
    )

    return {
        "schema": "radio_op31c_daily_summary_v1",
        "generated_at_utc": _utc_now(),
        "chain_ok": ok,
        "missing_artifacts": missing,
        "briefing_id_morning": morning.get("briefing_id"),
        "briefing_id_friday": friday.get("briefing_id"),
        "briefing_id_health": health.get("briefing_id"),
        "gate_ok_morning": gate_m.get("gate_ok"),
        "gate_ok_friday": gate_f.get("gate_ok"),
        "gate_ok_health": gate_h.get("gate_ok"),
        "gate_reasons_morning": gate_m.get("reasons") or [],
        "gate_reasons_friday": gate_f.get("reasons") or [],
        "gate_reasons_health": gate_h.get("reasons") or [],
        "optional_missing": [k for k in ("morning_mp3", "friday_mp3", "health_mp3", "video_bed") if not files.get(k, {}).get("exists")],
        "rtmp_url_configured": rtmp_ok,
        "rtmp_command_live": _rtmp_command_live(root),
        "zone_a_live_stage": _live_stage(rtmp_ok, smoke_ok),
        "zone_a_rtmp_smoke_ok": smoke_ok,
        "files": files,
        "friday_narrative_fuel": bool((friday.get("upstream_inputs") or {}).get("narrative_fuel")),
        "next_manual": _next_manual_steps(rtmp_ok, smoke_ok),
    }


def _next_manual_steps(rtmp_ok: bool, smoke_ok: bool | None) -> List[str]:
    steps = [
        "YouTube Studio: paste reports/radio_youtube_studio_paste_latest.txt (mkm_radio + zone_a blocks)",
        "Upload Shorts: reports/radio_dialogue_merged_latest.mp3 + reports/radio_dialogue_script_morning_shorts_latest.srt",
        "Upload VOD: reports/radio_dialogue_friday_merged_latest.mp3 + reports/radio_dialogue_script_friday_vod_latest.srt",
    ]
    if not rtmp_ok:
        steps.append(
            "L1: pwsh -File scripts\\Set-YoutubeRtmpUrlUserEnv_v1.ps1 -FromDotEnv "
            "then pwsh -File scripts\\Invoke-ZoneALiveBroadcastPrep_v1.ps1 -SkipContentRefresh"
        )
    else:
        steps.append("L2: Studio — stream Ready (비공개 테스트 권장)")
        if smoke_ok is not True:
            steps.append(
                "L3: py scripts/run_ambient_stream_rtmp_smoke_v1.py --seconds 30 (Studio Ready 후)"
            )
        else:
            steps.append(
                "L4: pwsh -File scripts\\Invoke-ZoneALiveBroadcastPrep_v1.ps1 -SkipContentRefresh -GoLive (24h)"
            )
    steps.insert(
        0,
        "L0.5: py scripts/run_ambient_stream_quality_audit_v1.py --write-preview "
        "(local MP4; no RTMP cost)",
    )
    steps.append("BED probe: py scripts/run_ambient_stream_ffmpeg_probe_v1.py --probe-seconds 5")
    return steps


def main() -> int:
    ap = argparse.ArgumentParser(description="Build O-P31c daily summary JSON.")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = build_summary(args.root)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0 if doc.get("chain_ok") else 1
    out = args.out_json if args.out_json.is_absolute() else args.root / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")
    print(str(out))
    return 0 if doc.get("chain_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
