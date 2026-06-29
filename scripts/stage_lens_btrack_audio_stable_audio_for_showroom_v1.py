#!/usr/bin/env python3
"""Stage lens B-track Stable Audio Open 12×3 WAV matrix into showroom staging (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC_DIR = ROOT / "reports/track_c_audio_hook_samples_v1/stable_audio_open_v1"
BAKE_REPORT = SRC_DIR / "lens_btrack_audio_stable_audio_bake_report_v1_latest.json"
STAGING = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging"
AUDIO_DEST = STAGING / "audio/lens_btrack/stable_audio_open/v1"
MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"

from scripts.lens_btrack_playback_matrix_v1 import (  # noqa: E402
    audio_filename,
    audio_playback_id,
    iter_matrix_pairs,
)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_manifest(*, staged_files: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": "showroom_lens_stable_audio_matrix_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "generator": "stable_audio_open",
        "production_lut_unchanged": True,
        "generated_at_utc": _utc_now_z(),
        "showroom_assets_base": "./audio/lens_btrack/stable_audio_open/v1/",
        "clip_count": len(staged_files),
        "matrix_complete": len(staged_files) >= 12,
        "clips": staged_files,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    clips_src: list[dict[str, object]] = []
    if BAKE_REPORT.is_file():
        doc = json.loads(BAKE_REPORT.read_text(encoding="utf-8"))
        raw = doc.get("clips") if isinstance(doc.get("clips"), list) else []
        for row in raw:
            if isinstance(row, dict) and row.get("file"):
                clips_src.append(row)

    if not clips_src:
        for sasang, mode in iter_matrix_pairs():
            fname = audio_filename(sasang, mode)
            clips_src.append(
                {
                    "file": fname,
                    "sasang_primary": sasang,
                    "showroom_display_mode": mode,
                    "playback_id": audio_playback_id(sasang, mode),
                    "generator": "stable_audio_open",
                    "status": "ok",
                }
            )

    if not args.dry_run:
        AUDIO_DEST.mkdir(parents=True, exist_ok=True)

    staged: list[dict[str, object]] = []
    missing = 0
    for row in clips_src:
        fname = str(row.get("file") or "")
        if not fname:
            continue
        src = SRC_DIR / fname
        if not src.is_file():
            missing += 1
            continue
        dest = AUDIO_DEST / fname
        if args.dry_run:
            print(f"[stable-audio-stage] WHATIF {src} -> {dest}")
        else:
            shutil.copy2(src, dest)
            print(f"[stable-audio-stage] OK {dest}")
        entry = dict(row)
        entry["showroom_url"] = f"./audio/lens_btrack/stable_audio_open/v1/{fname}"
        staged.append(entry)

    manifest = _build_manifest(staged_files=staged)
    out_json = MVP / "showroom_lens_stable_audio_matrix_v1.json"
    if args.dry_run:
        print(f"[stable-audio-stage] WHATIF manifest -> {out_json} ({len(staged)} wav)")
    else:
        out_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[stable-audio-stage] WROTE {out_json} ({len(staged)} wav, missing={missing})")

    if not staged:
        return 1
    if missing and len(staged) < 12:
        print(f"[stable-audio-stage] WARN: matrix incomplete ({len(staged)}/12)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
