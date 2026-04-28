#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KDD submission-ready template payload.")
    ap.add_argument(
        "--recommended-track-json",
        default="docs/final/artifacts/two_track_submission_recommended_track_latest.json",
    )
    ap.add_argument(
        "--camera-ready-json",
        default="docs/final/artifacts/two_track_submission_camera_ready_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/two_track_kdd_submission_template_latest.json",
    )
    args = ap.parse_args()

    rp = resolve(args.recommended_track_json)
    cp = resolve(args.camera_ready_json)
    op = resolve(args.output_json)
    if not rp.is_file():
        raise SystemExit(f"missing recommended track json: {rp}")
    if not cp.is_file():
        raise SystemExit(f"missing camera ready json: {cp}")

    rec = load(rp)
    cam = load(cp)

    title = str(rec.get("selected_title_en") or cam.get("recommended_title_en") or "").strip()
    abstract = str(rec.get("selected_abstract_en_180w") or "").strip()
    if not abstract:
        compact = cam.get("compressed_abstracts_en") if isinstance(cam.get("compressed_abstracts_en"), dict) else {}
        abstract = str(compact.get("kdd_180w") or "").strip()

    keywords = cam.get("keywords_en") if isinstance(cam.get("keywords_en"), list) else []
    keywords = [str(k).strip() for k in keywords if str(k).strip()]

    contributions = [
        "Two-track architecture that separates narrative insight generation from execution gating.",
        "Falsification-first validation with explicit fail-boundary and rollback semantics.",
        "Public-safe disclosure strategy with artifact-chain reproducibility for applied review.",
    ]

    submission_notes = [
        "Use this payload for KDD Applied Data Science track form fields.",
        "Keep proprietary formulas/weights redacted; cite artifact paths instead.",
        "Include fail-boundary row in supplementary/rebuttal appendix.",
    ]

    out = {
        "schema": "two_track_kdd_submission_template_v1",
        "generated_at_utc": now(),
        "track": "kdd_applied_data_science",
        "title_en": title,
        "abstract_en_180w": abstract,
        "keywords_en": keywords,
        "contributions_en": contributions,
        "submission_notes_en": submission_notes,
        "source": {
            "recommended_track_json": str(rp),
            "camera_ready_json": str(cp),
        },
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

