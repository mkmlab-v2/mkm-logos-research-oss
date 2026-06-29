#!/usr/bin/env python3
"""Stage lens B-track A/B smoke WAV + JSON into showroom staging (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AB_DIR = ROOT / "reports/track_c_audio_hook_samples_v1/ab_generator_smoke_v1"
AB_REPORT = AB_DIR / "lens_btrack_audio_generator_ab_smoke_v1_latest.json"
STAGING = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/.showroom_staging"
MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
AUDIO_DEST = STAGING / "audio/lens_btrack/ab_smoke/v1"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not AB_REPORT.is_file():
        print(f"[ab-stage] missing report: {AB_REPORT}", file=sys.stderr)
        return 2

    doc = json.loads(AB_REPORT.read_text(encoding="utf-8"))
    gens = doc.get("generators") if isinstance(doc.get("generators"), dict) else {}
    copied: list[str] = []

    if not args.dry_run:
        AUDIO_DEST.mkdir(parents=True, exist_ok=True)

    for key in ("musicgen", "stable_audio_open"):
        row = gens.get(key) if isinstance(gens.get(key), dict) else {}
        src = Path(str(row.get("path") or ""))
        if not src.is_file():
            continue
        dest_name = src.name
        dest = AUDIO_DEST / dest_name
        if args.dry_run:
            print(f"[ab-stage] WHATIF {src} -> {dest}")
        else:
            shutil.copy2(src, dest)
            print(f"[ab-stage] OK {dest}")
        copied.append(dest_name)
        row["showroom_url"] = f"./audio/lens_btrack/ab_smoke/v1/{dest_name}"

    doc["staged_at_utc"] = _utc_now_z()
    doc["showroom_assets_base"] = "./audio/lens_btrack/ab_smoke/v1/"
    out_json = MVP / "showroom_lens_audio_ab_smoke_v1.json"
    if args.dry_run:
        print(f"[ab-stage] WHATIF report -> {out_json}")
    else:
        out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ab-stage] WROTE {out_json} ({len(copied)} wav)")

    return 0 if copied else 1


if __name__ == "__main__":
    raise SystemExit(main())
