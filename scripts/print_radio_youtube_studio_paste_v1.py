#!/usr/bin/env python3
"""Print YouTube Studio paste blocks from radio_youtube_channel_copy_v1_latest.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "radio_youtube_channel_copy_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "radio_youtube_studio_paste_latest.txt"


def _block(title: str, body: str) -> str:
    return f"=== {title} ===\n{body.strip()}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Print Studio paste blocks for MKM/TKM channels.")
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-txt", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    path = args.in_json if args.in_json.is_absolute() else ROOT / args.in_json
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    channels = doc.get("channels") or {}
    parts = [
        f"generated_at_utc: {doc.get('generated_at_utc')}",
        f"public_facing_version: {doc.get('public_facing_version')}",
        "",
    ]
    for skin_id in ("mkm_radio", "tkm_health_24h", "zone_a_ambient_24h"):
        ch = channels.get(skin_id) or {}
        if not ch:
            continue
        parts.append(
            _block(
                f"{skin_id} · channel name",
                f"{ch.get('display_name_primary', '')}\n{ch.get('display_name_secondary', '')}",
            )
        )
        parts.append(_block(f"{skin_id} · description_ko", str(ch.get("description_ko") or "")))
        parts.append(_block(f"{skin_id} · live_stream_title_ko", str(ch.get("live_stream_title_ko") or "")))
        tags = ", ".join(ch.get("tags_ko") or [])
        shorts = " ".join(ch.get("shorts_hashtags") or [])
        parts.append(_block(f"{skin_id} · tags_ko", tags))
        parts.append(_block(f"{skin_id} · shorts_hashtags", shorts))
        if ch.get("youtube_handle_url"):
            parts.append(_block(f"{skin_id} · handle", str(ch["youtube_handle_url"])))
        parts.append("")
    for line in doc.get("studio_paste_order") or []:
        parts.append(f"• {line}")
    upload_rows = [
        ("MKM Shorts", "reports/radio_dialogue_merged_latest.mp3", "reports/radio_dialogue_script_morning_shorts_latest.srt"),
        ("MKM Friday VOD", "reports/radio_dialogue_friday_merged_latest.mp3", "reports/radio_dialogue_script_friday_vod_latest.srt"),
        ("TKM health Shorts", "reports/radio_dialogue_health_merged_latest.mp3", "(optional — no SRT path in chain)"),
    ]
    parts.append("")
    parts.append("=== UPLOAD HANDOFF (YouTube Studio · files under repo root) ===")
    for label, mp3_rel, srt_rel in upload_rows:
        mp3 = ROOT / mp3_rel
        srt = ROOT / srt_rel if not srt_rel.startswith("(") else None
        mp3_line = f"{mp3_rel}  exists={mp3.is_file()}  bytes={mp3.stat().st_size if mp3.is_file() else 0}"
        srt_line = (
            f"{srt_rel}  exists={srt.is_file()}  bytes={srt.stat().st_size if srt.is_file() else 0}"
            if srt
            else srt_rel
        )
        parts.append(f"{label}:")
        parts.append(f"  audio: {mp3_line}")
        parts.append(f"  subs:  {srt_line}")
    rtmp_ok = bool(__import__("os").environ.get("YOUTUBE_RTMP_URL", "").strip())
    parts.append(
        f"RTMP: YOUTUBE_RTMP_URL configured={rtmp_ok} — cmd: reports/ambient_stream_rtmp_command_latest.txt"
    )
    parts.append("Live prep: pwsh -File scripts/Invoke-ZoneALiveBroadcastPrep_v1.ps1 [-Render] [-GoLive]")
    text = "\n".join(parts).strip() + "\n"
    if args.stdout_only:
        print(text, end="")
        return 0
    out = args.out_txt if args.out_txt.is_absolute() else ROOT / args.out_txt
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
