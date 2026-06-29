# Keywords: showroom, lens_media, lens_video, lens_audio, public-event, thin_slice
"""Build lens audio + video observability blocks and combined media thin slice doc."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.build_showroom_lens_audio_observability_v1 as audio_mod

DEFAULT_AUDIO_OUT = ROOT / "docs/final/artifacts/showroom_lens_audio_observability_v1_latest.json"
DEFAULT_VIDEO_OUT = ROOT / "docs/final/artifacts/showroom_lens_video_observability_v1_latest.json"
DEFAULT_MEDIA_SLICE_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_lens_media_thin_slice_v1.json"
)
AUDIO_SLICE_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_lens_audio_thin_slice_v1.json"
)
VIDEO_LUT_EXAMPLE = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1.example.json"
VIDEO_LUT_LATEST = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"
DEFAULT_MACRO_SLICE = ROOT / "docs/final/artifacts/showroom_macro_horizon_2030_slice_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_week() -> str:
    return datetime.now(timezone.utc).strftime("%G-W%V")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _ensure_video_lut_latest() -> dict[str, Any]:
    lut = _read_json(VIDEO_LUT_LATEST)
    if lut.get("schema") == "jemaai_lens_video_playback_lut_v1":
        return lut
    ex = _read_json(VIDEO_LUT_EXAMPLE)
    if ex.get("schema") == "jemaai_lens_video_playback_lut_v1":
        VIDEO_LUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
        VIDEO_LUT_LATEST.write_text(json.dumps(ex, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ex
    return {}


def _video_playback_id_from_audio(audio_playback_id: str) -> str:
    return re.sub(r"^LM_", "LV_", str(audio_playback_id or ""), count=1)


def _pick_video_playback_id(lut: dict[str, Any], audio_playback_id: str, display_mode: str) -> str:
    entries = lut.get("entries") if isinstance(lut.get("entries"), dict) else {}
    candidate = _video_playback_id_from_audio(audio_playback_id)
    if candidate in entries:
        return candidate
    mode = display_mode.strip().lower()
    for vid, row in entries.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("showroom_display_mode") or "").lower() == mode:
            return str(vid)
    if entries:
        return next(iter(entries.keys()))
    return candidate


def build_lens_video_observability(
    audio_block: dict[str, Any],
    *,
    lut_path: Path | None = None,
) -> dict[str, Any]:
    lut = _read_json(lut_path) if lut_path else _ensure_video_lut_latest()
    if lut.get("schema") != "jemaai_lens_video_playback_lut_v1":
        lut = _ensure_video_lut_latest()

    display_mode = str(audio_block.get("showroom_display_mode_bind") or "idle").lower()
    audio_pid = str(audio_block.get("playback_id") or "")
    video_pid = _pick_video_playback_id(lut, audio_pid, display_mode)
    lut_version = str(lut.get("version") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    audio_gate = audio_block.get("gate") if isinstance(audio_block.get("gate"), dict) else {}
    decision = str(audio_gate.get("decision") or "WATCH").upper()
    ref = str(audio_gate.get("audio_gate_report_ref") or "00000000")
    if not re.match(r"^[a-f0-9]{8,16}$", ref):
        ref = "00000000"

    cm = audio_block.get("conditioning_meta") if isinstance(audio_block.get("conditioning_meta"), dict) else {}
    sasang = str(cm.get("sasang_primary") or "soyang").lower()

    return {
        "schema": "public_event_lens_video_thin_slice_v1",
        "hypothesis_class": "HYPO",
        "track_wall": "B_track_research_only",
        "non_gating": True,
        "clinical_claims": False,
        "video_playback_id": video_pid,
        "audio_playback_id_mirror": audio_pid,
        "playback_lut_version": f"jemaai_lens_video_playback_lut_v1@{lut_version}",
        "showroom_display_mode_bind": display_mode,
        "gate": {
            "decision": decision if decision in ("PASS", "HOLD", "WATCH") else "WATCH",
            "video_gate_report_ref": ref,
            "loop_seamlessness_pass": bool(audio_gate.get("loop_seamlessness_pass", False)),
            "visual_alignment_pass": bool(audio_gate.get("lens_alignment_pass", False)),
            "commercial_license_verified": bool(audio_gate.get("commercial_license_verified", False)),
        },
        "conditioning_meta": {
            "sasang_primary": sasang if sasang in ("soyang", "taeyang", "taeeum", "soeum") else "soyang",
            "showroom_display_mode": display_mode,
        },
        "disclaimer_ref": "jemaai_lens_video_hypo_v1",
        "generated_at_utc": audio_block.get("generated_at_utc") or _utc_now_z(),
        "baked_asset_week": audio_block.get("baked_asset_week") or _iso_week(),
    }


def build_media_thin_slice_doc(
    audio_block: dict[str, Any],
    video_block: dict[str, Any],
    audio_lut: dict[str, Any],
    video_lut: dict[str, Any],
) -> dict[str, Any]:
    audio_pid = audio_block.get("playback_id")
    video_pid = video_block.get("video_playback_id")
    a_entries = audio_lut.get("entries") if isinstance(audio_lut.get("entries"), dict) else {}
    v_entries = video_lut.get("entries") if isinstance(video_lut.get("entries"), dict) else {}
    a_entry = a_entries.get(audio_pid, {}) if audio_pid in a_entries else {}
    v_entry = v_entries.get(video_pid, {}) if video_pid in v_entries else {}
    a_base = str(audio_lut.get("assets_base_url") or "")
    v_base = str(video_lut.get("assets_base_url") or "")
    a_file = str(a_entry.get("file") or "")
    v_file = str(v_entry.get("file") or "")

    return {
        "schema": "showroom_lens_media_thin_slice_v1",
        "hypothesis_tag": "[HYPO]",
        "track_wall": "B_track_research_only",
        "generated_at_utc": video_block.get("generated_at_utc"),
        "lens_audio_observability_v1": audio_block,
        "lens_video_observability_v1": video_block,
        "playback_lut": {
            "audio": {
                "version": audio_lut.get("version"),
                "playback_id": audio_pid,
                "public_asset_url": f"{a_base}{a_file}" if a_base and a_file else None,
                "entry": a_entry,
            },
            "video": {
                "version": video_lut.get("version"),
                "video_playback_id": video_pid,
                "public_asset_url": f"{v_base}{v_file}" if v_base and v_file else None,
                "entry": v_entry,
            },
        },
        "boundary_note": (
            "Pre-baked static audio+video loop lookup only. Not live MusicGen/AnimateDiff. "
            "Not clinical. Not a trading signal. Logos/medical/live-trading walls remain NON_GATING / blocked."
        ),
    }


def _apply_macro_slice_bind(
    macro_path: Path,
    *,
    display_mode: str,
    sasang_primary: str,
) -> tuple[str, str]:
    bind = _read_json(macro_path).get("lens_media_bind")
    if not isinstance(bind, dict):
        return display_mode, sasang_primary
    mode = str(bind.get("showroom_display_mode") or display_mode).lower()
    sasang = sasang_primary if sasang_primary else str(bind.get("sasang_primary") or "")
    return mode, sasang


def main() -> int:
    p = argparse.ArgumentParser(description="Build lens media (audio+video) observability for public-event.v1")
    p.add_argument("--showroom-display-mode", default="idle", help="idle|defend|attack")
    p.add_argument("--sasang-primary", default="", help="soyang|taeyang|taeeum|soeum override")
    p.add_argument(
        "--from-macro-slice",
        nargs="?",
        const=str(DEFAULT_MACRO_SLICE),
        default=None,
        help="Read lens_media_bind from macro slice JSON (default path when flag alone)",
    )
    p.add_argument("--audio-out-json", type=Path, default=DEFAULT_AUDIO_OUT)
    p.add_argument("--video-out-json", type=Path, default=DEFAULT_VIDEO_OUT)
    p.add_argument("--media-slice-out", type=Path, default=DEFAULT_MEDIA_SLICE_OUT)
    p.add_argument("--audio-lut", type=Path, default=None)
    p.add_argument("--video-lut", type=Path, default=None)
    p.add_argument("--stdout-only", action="store_true")
    args = p.parse_args()

    display_mode = args.showroom_display_mode
    sasang_primary = args.sasang_primary
    if args.from_macro_slice is not None:
        macro_path = Path(args.from_macro_slice)
        display_mode, sasang_primary = _apply_macro_slice_bind(
            macro_path,
            display_mode=display_mode,
            sasang_primary=sasang_primary,
        )

    audio_block = audio_mod.build_lens_audio_observability(
        showroom_display_mode=display_mode,
        lut_path=args.audio_lut,
        sasang_primary=sasang_primary or None,
    )
    audio_lut = audio_mod._ensure_lut_latest()
    video_lut = _read_json(args.video_lut) if args.video_lut else _ensure_video_lut_latest()
    video_block = build_lens_video_observability(audio_block, lut_path=args.video_lut)
    media_slice = build_media_thin_slice_doc(audio_block, video_block, audio_lut, video_lut)
    audio_slice = audio_mod.build_thin_slice_doc(audio_block, audio_lut)

    if args.stdout_only:
        print(json.dumps({"audio": audio_block, "video": video_block}, ensure_ascii=False, indent=2))
        return 0

    args.audio_out_json.parent.mkdir(parents=True, exist_ok=True)
    args.video_out_json.parent.mkdir(parents=True, exist_ok=True)
    args.media_slice_out.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_SLICE_OUT.parent.mkdir(parents=True, exist_ok=True)

    args.audio_out_json.write_text(json.dumps(audio_block, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.video_out_json.write_text(json.dumps(video_block, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.media_slice_out.write_text(json.dumps(media_slice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIO_SLICE_OUT.write_text(json.dumps(audio_slice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[lens-media-obs] WROTE: {args.audio_out_json}")
    print(f"[lens-media-obs] WROTE: {args.video_out_json}")
    print(f"[lens-media-obs] WROTE: {args.media_slice_out}")
    print(
        f"[lens-media-obs] audio={audio_block.get('playback_id')} "
        f"video={video_block.get('video_playback_id')} "
        f"gate={video_block.get('gate', {}).get('decision')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
