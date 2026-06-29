#!/usr/bin/env python3
"""Export slim lens media playback index for mkmlife public /data (12 pairs)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"
VIDEO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"
DEFAULT_OUT = ROOT / "projects/mkm/mkm-life/public/data/lens_media_playback_mkmlife_v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_slice() -> dict[str, Any]:
    audio = _load(AUDIO_LUT)
    video = _load(VIDEO_LUT)
    audio_base = str(audio.get("assets_base_url") or "").rstrip("/") + "/"
    video_base = str(video.get("assets_base_url") or "").rstrip("/") + "/"
    av = str(audio.get("version") or "")
    vv = str(video.get("version") or "")
    entries: dict[str, Any] = {}
    for key, meta in sorted((audio.get("entries") or {}).items()):
        if not isinstance(meta, dict):
            continue
        vk = key.replace("LM_", "LV_", 1)
        vmeta = (video.get("entries") or {}).get(vk) or {}
        audio_file = str(meta.get("file") or "")
        mp4_file = str(vmeta.get("mp4_file") or "")
        poster = str(vmeta.get("poster_file") or "")
        entries[key] = {
            "audio_url": f"{audio_base}{audio_file}?v={av}" if audio_file else None,
            "video_mp4_url": f"{video_base}{mp4_file}?v={vv}" if mp4_file else None,
            "poster_url": f"{video_base}{poster}?v={vv}" if poster else None,
            "duration_sec_audio": meta.get("duration_sec"),
            "duration_sec_video": vmeta.get("duration_sec"),
            "sasang_primary": meta.get("sasang_primary"),
            "showroom_display_mode": meta.get("showroom_display_mode"),
            "video_lut_key": vk if vmeta else None,
        }
    return {
        "schema": "lens_media_playback_mkmlife_v1",
        "hypothesis_class": "[HYPO]",
        "audio_lut_version": av,
        "video_lut_version": vv,
        "entries": entries,
        "refs": {
            "audio_lut": "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json",
            "video_lut": "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="mkmlife lens media playback slice")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_slice()
    out = args.output_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(out), "entries": len(doc["entries"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
