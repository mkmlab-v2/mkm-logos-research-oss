#!/usr/bin/env python3
"""HEAD + local WAV duration smoke for lens media hub 12 pairs."""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AUDIO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_audio_playback_lut_v1_latest.json"
VIDEO_LUT = ROOT / "docs/final/artifacts/jemaai_lens_video_playback_lut_v1_latest.json"
WAV_DIR = ROOT / "reports/track_c_audio_hook_samples_v1"
HTML = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_lens_media_thin_slice_v1.html"
)


def _head(url: str) -> int:
    req = Request(
        url,
        method="HEAD",
        headers={"User-Agent": "MKM-LensMediaHubQA/1.0"},
    )
    with urlopen(req, timeout=20) as resp:
        return int(resp.status)


def _html_structure_checks(html: str, fails: list[str]) -> None:
    if 'html += "</div><h2>사상 4체질</h2><div class="chip-row"' in html:
        fails.append("html inline JS quote break (sasang-chips line)")
    if 'type="video/mp4"' not in html:
        fails.append("html missing mp4 source")
    if "aSuffix" not in html:
        fails.append("html missing audio cache bust")
    mp4_i = html.find("video/mp4")
    webm_i = html.find("video/webm")
    if mp4_i < 0 or webm_i < 0 or mp4_i > webm_i:
        fails.append("mp4 not listed before webm in template")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Lens media hub live QA (12 pairs).")
    ap.add_argument(
        "--offline",
        action="store_true",
        help="Skip live HEAD checks; local WAV + HTML structure only.",
    )
    args = ap.parse_args()

    fails: list[str] = []
    alu = json.loads(AUDIO_LUT.read_text(encoding="utf-8"))
    vlu = json.loads(VIDEO_LUT.read_text(encoding="utf-8"))
    av = str(alu.get("version") or "")
    vv = str(vlu.get("version") or "")
    min_dur = float(alu.get("clip_seconds") or 28) - 4.0

    for k in sorted(alu.get("entries", {})):
        a = alu["entries"][k]
        vk = k.replace("LM_", "LV_")
        v = vlu.get("entries", {}).get(vk, {})
        wav = WAV_DIR / str(a.get("file") or "")
        if wav.is_file():
            with wave.open(str(wav), "rb") as w:
                dur = w.getnframes() / float(w.getframerate())
            if dur < min_dur:
                fails.append(f"{k} local_dur={dur:.1f}s (<{min_dur})")
        if not args.offline:
            for label, url in (
                ("wav", f"https://jemaai.cloud/audio/lens_btrack/v1/{a['file']}?v={av}"),
                ("webm", f"https://jemaai.cloud/video/lens_btrack/v1/{v.get('file', '')}?v={vv}"),
                ("mp4", f"https://jemaai.cloud/video/lens_btrack/v1/{v.get('mp4_file', '')}?v={vv}"),
            ):
                if label != "wav" and not v.get("file"):
                    continue
                try:
                    if _head(url) != 200:
                        fails.append(f"{k} {label} status!=200")
                except OSError as exc:
                    fails.append(f"{k} {label} {exc}")

    html = HTML.read_text(encoding="utf-8")
    _html_structure_checks(html, fails)

    if fails:
        print("[lens-media-qa] FAIL", flush=True)
        for f in fails:
            print(f"  - {f}", flush=True)
        return 1
    print(
        f"[lens-media-qa] OK pairs={len(alu.get('entries', {}))} "
        f"audio_ver={av} clip_seconds={alu.get('clip_seconds')}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
